"""Composition root: the only place that wires I/O to the pure core (spec §5.2, §11.1)."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from contextvars import ContextVar
from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
from typing import Annotated, NoReturn

import typer

from seamscan import __version__
from seamscan.analysis import Analysis, analyze
from seamscan.model import ChangeSet, Finding, SourceFile
from seamscan.policy.baseline import (
    Baseline,
    BaselineError,
    added_since,
    from_findings,
    parse_baseline,
    prune,
    render_baseline,
)
from seamscan.policy.config import Config, ConfigError, parse_config
from seamscan.policy.verdict import INTERNAL_ERROR_RULES, Verdict, decide
from seamscan.report.json import render_json
from seamscan.report.terminal import render_terminal
from seamscan.rules.registry import RULES
from seamscan.workspace.files import collect
from seamscan.workspace.git import GitError, read_changeset, read_file_at

app = typer.Typer(add_completion=False, no_args_is_help=True)
baseline_app = typer.Typer(no_args_is_help=True)
app.add_typer(
    baseline_app, name="baseline", help="Record existing findings as accepted debt (the ratchet)."
)

# Both files live at the root a command analyzes: the working directory for `scan`, PATH
# for `audit` and `baseline`. Finding paths are relative to that root, so the baseline's
# must be too, or audit and scan would disagree about what is known.
CONFIG_FILE = "seamscan.toml"
BASELINE_FILE = ".seamscan/baseline.json"


class Format(StrEnum):
    terminal = "terminal"
    json = "json"


FormatOpt = Annotated[Format, typer.Option("--format", help="Output format")]
OutputOpt = Annotated[
    Path | None, typer.Option("--output", help="Write to a file instead of stdout")
]


@dataclass(frozen=True)
class Outcome:
    """Everything one run produced; every output format renders from this."""

    analysis: Analysis
    verdict: Verdict
    skipped: tuple[tuple[str, str], ...]  # (path, reason) from file collection


@dataclass(frozen=True)
class _Globals:
    config: Path | None = None  # --config


# Set by the root callback for the length of one invocation, so `_run` sees global options
# whichever command called it, without a parameter threaded through every command.
_GLOBALS: ContextVar[_Globals] = ContextVar("seamscan_globals", default=_Globals())


def _fail(message: str, code: int = 2) -> NoReturn:
    typer.echo(f"seamscan: {message}", err=True)
    raise typer.Exit(code=code)


def _read(path: Path, what: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        reason = exc.strerror if isinstance(exc, OSError) else str(exc)
        _fail(f"cannot read {what} {path}: {reason}")


def _load_config(root: Path) -> Config:
    explicit = _GLOBALS.get().config
    path = explicit or root / CONFIG_FILE
    if explicit is None and not path.exists():
        return Config()
    try:
        return parse_config(_read(path, "config"), frozenset(r.meta.id for r in RULES))
    except ConfigError as exc:
        _fail(f"{path}: {exc}")


def _load_baseline(root: Path) -> Baseline:
    path = root / BASELINE_FILE
    if not path.exists():
        return Baseline(())
    try:
        return parse_baseline(_read(path, "baseline"))
    except BaselineError as exc:
        _fail(f"{path}: {exc}")


def _analyze(
    config: Config,
    files: Sequence[SourceFile],
    change: ChangeSet | None = None,
    context: Sequence[SourceFile] = (),
) -> Analysis:
    """`analyze` under the repository's config: rules off, paths excluded, severities set."""
    analysis = analyze(
        [f for f in files if not config.excludes(f.path)],
        change=change,
        rules=tuple(r for r in RULES if r.meta.id not in config.disabled),
        context=[f for f in context if not config.excludes(f.path)],
    )
    # `replace`, so any other Analysis fields pass through untouched.
    return replace(
        analysis,
        findings=config.override_severity(analysis.findings),
        suppressed=config.override_severity(analysis.suppressed),
    )


def _run(
    root: Path,
    files: Sequence[SourceFile],
    skipped: tuple[tuple[str, str], ...],
    change: ChangeSet | None = None,
    context: Sequence[SourceFile] = (),
) -> Outcome:
    """The one path from files to a verdict, shared by every command.

    Reads `seamscan.toml` (or --config) and the baseline at `root`. A bad one prints the
    reason and raises typer.Exit(2): it is never ignored.
    """
    config = _load_config(root)
    known = _load_baseline(root).fingerprints()
    analysis = _analyze(config, files, change, context)
    verdict = decide(analysis.findings, config.policy, known)
    return Outcome(analysis, verdict, tuple(s for s in skipped if not config.excludes(s[0])))


def _render(outcome: Outcome, fmt: Format) -> str:
    findings = outcome.analysis.findings
    if fmt is Format.json:
        return render_json(findings, outcome.verdict, __version__)
    return render_terminal(findings, outcome.verdict)


def _emit(outcome: Outcome, fmt: Format, output: Path | None) -> None:
    text = _render(outcome, fmt)
    if output:
        output.write_text(text)
    else:
        sys.stdout.write(text)
    raise typer.Exit(code=outcome.verdict.exit_code)


@app.command()
def audit(
    path: Annotated[Path, typer.Argument(help="Repository root")] = Path("."),
    fmt: FormatOpt = Format.terminal,
    output: OutputOpt = None,
) -> None:
    """Check a whole repository."""
    root = path.resolve()
    fileset = collect(root)
    _emit(_run(root, fileset.files, fileset.skipped), fmt, output)


@app.command()
def scan(
    base: Annotated[str | None, typer.Option(help="Compare against this git ref")] = None,
    staged: Annotated[bool, typer.Option(help="Check only staged changes")] = False,
    fmt: FormatOpt = Format.terminal,
    output: OutputOpt = None,
) -> None:
    """Check only what a change introduced (working tree vs HEAD by default)."""
    root = Path.cwd()
    try:
        change: ChangeSet = read_changeset(root, base=base, staged=staged)
    except GitError as exc:
        typer.echo(f"seamscan: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    fileset = collect(root)
    changed = tuple(f for f in fileset.files if f.path in change.added)
    outcome = _run(root, changed, fileset.skipped, change=change, context=fileset.files)
    _emit(outcome, fmt, output)


RootArg = Annotated[Path, typer.Argument(help="Repository root")]


def _entries(n: int) -> str:
    return f"{n} entry" if n == 1 else f"{n} entries"


def _current_findings(root: Path) -> tuple[Finding, ...]:
    """A full audit of `root` under its config, as the baseline commands record it.

    Refuses (exit 3) when a rule crashed: the findings it would have made are missing, so
    a baseline written now would be incomplete, and pruning would drop live entries.
    """
    fileset = collect(root)
    findings = _analyze(_load_config(root), fileset.files).findings
    crashed = [f for f in findings if f.rule_id in INTERNAL_ERROR_RULES]
    for f in crashed:
        typer.echo(f"seamscan: {f.message}", err=True)
    if crashed:
        _fail("a rule crashed, so the baseline would be incomplete; not writing it", code=3)
    return findings


def _write_baseline(root: Path, baseline: Baseline) -> None:
    path = root / BASELINE_FILE
    path.parent.mkdir(exist_ok=True)
    path.write_text(render_baseline(baseline), encoding="utf-8", newline="\n")


@baseline_app.command("create")
def baseline_create(path: RootArg = Path(".")) -> None:
    """Record every current finding in .seamscan/baseline.json, replacing what was there."""
    root = path.resolve()
    baseline = from_findings(_current_findings(root))
    _write_baseline(root, baseline)
    typer.echo(f"Wrote {_entries(len(baseline.entries))} to {BASELINE_FILE}")


@baseline_app.command("prune")
def baseline_prune(path: RootArg = Path(".")) -> None:
    """Drop baseline entries that no longer match any finding."""
    root = path.resolve()
    if not (root / BASELINE_FILE).exists():
        _fail(f"no baseline at {root / BASELINE_FILE}; run `seamscan baseline create` first")
    old = _load_baseline(root)
    new = prune(old, _current_findings(root))
    _write_baseline(root, new)
    removed = len(old.entries) - len(new.entries)
    typer.echo(f"Removed {_entries(removed)}; {len(new.entries)} remain")


@baseline_app.command("check")
def baseline_check(
    against: Annotated[str, typer.Option("--against", help="Base git ref, e.g. origin/main")],
    path: RootArg = Path("."),
) -> None:
    """Fail if the baseline gained entries compared with the one at REF (the ratchet)."""
    root = path.resolve()
    current = _load_baseline(root)
    try:
        text = read_file_at(root, against, BASELINE_FILE)
    except GitError as exc:
        _fail(str(exc))
    try:
        base = Baseline(()) if text is None else parse_baseline(text)
    except BaselineError as exc:
        _fail(f"{BASELINE_FILE} at {against}: {exc}")
    added = added_since(current, base)
    if not added:
        typer.echo(f"Baseline has no new entries compared with {against}")
        return
    lines = [f"Baseline gained {_entries(len(added))} compared with {against}:"]
    lines += [f"  {e.path}  {e.rule_id}  {e.fingerprint}" for e in added]
    lines.append("Fix them instead, or have a reviewer accept the baseline change on purpose.")
    typer.echo("\n".join(lines))
    raise typer.Exit(code=1)


def _show_version(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def _root(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            help="Show version and exit",
            callback=_show_version,
            is_eager=True,  # runs before Typer insists on a subcommand
        ),
    ] = False,
    config: Annotated[
        Path | None,
        typer.Option("--config", help=f"Use this file instead of {CONFIG_FILE} at the root"),
    ] = None,
) -> None:
    """Static checks for the failures AI coding tools ship. See docs/SPEC.md."""
    token = _GLOBALS.set(_Globals(config=config))
    ctx.call_on_close(lambda: _GLOBALS.reset(token))


def main() -> None:
    app()
