"""Composition root: the only place that wires I/O to the pure core (spec §5.2, §11.1)."""

from __future__ import annotations

import difflib
import os
import sys
import traceback
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from importlib.resources import files as package_files
from pathlib import Path
from typing import Annotated

import typer

from seamscan import __version__
from seamscan.analysis import Analysis, analyze
from seamscan.hooks.claude import EditCheck, HookInputError, read_input, respond
from seamscan.model import ChangeSet, SourceFile
from seamscan.policy.verdict import Policy, Verdict, decide
from seamscan.report.agent import render_agent
from seamscan.report.catalog import render_rule_json, render_rule_table
from seamscan.report.json import render_json
from seamscan.report.terminal import render_terminal
from seamscan.rules.registry import RULES
from seamscan.workspace.files import collect
from seamscan.workspace.git import GitError, read_changeset, repo_root, unknown_paths

app = typer.Typer(add_completion=False, no_args_is_help=True)


class Format(StrEnum):
    terminal = "terminal"
    json = "json"
    agent = "agent"


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


def _run(
    root: Path,
    files: Sequence[SourceFile],
    skipped: tuple[tuple[str, str], ...],
    change: ChangeSet | None = None,
    context: Sequence[SourceFile] = (),
) -> Outcome:
    """The one path from files to a verdict, shared by every command."""
    analysis = analyze(files, change=change, context=context)
    verdict = decide(analysis.findings, Policy())
    return Outcome(analysis, verdict, skipped)


def _render(outcome: Outcome, fmt: Format) -> str:
    findings = outcome.analysis.findings
    if fmt is Format.json:
        return render_json(findings, outcome.verdict, __version__)
    if fmt is Format.agent:
        return render_agent(outcome.verdict)
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


def _scan_change(root: Path, change: ChangeSet) -> Outcome:
    fileset = collect(root)
    changed = tuple(f for f in fileset.files if f.path in change.added)
    return _run(root, changed, fileset.skipped, change=change, context=fileset.files)


def _repo_relative(root: Path, paths: Sequence[str | Path], base: Path) -> list[str | None]:
    """Each path as a repo-relative POSIX path, or None when it lies outside the repository.

    Only the parent directory is resolved: a symlinked dir (macOS /tmp) must still match
    git's real path, but a symlinked file is its own path in the repository.
    """
    result: list[str | None] = []
    for raw in paths:
        full = Path(os.path.abspath(base / raw))
        try:
            rel = (full.parent.resolve() / full.name).relative_to(root.resolve())
        except ValueError:
            result.append(None)
            continue
        result.append(rel.as_posix())
    return result


@app.command()
def scan(
    paths: Annotated[
        list[Path] | None, typer.Argument(help="Files to check, with --files", show_default=False)
    ] = None,
    base: Annotated[str | None, typer.Option(help="Compare against this git ref")] = None,
    staged: Annotated[bool, typer.Option(help="Check only staged changes")] = False,
    files: Annotated[
        bool, typer.Option("--files", help="Check only the files given as arguments")
    ] = False,
    fmt: FormatOpt = Format.terminal,
    output: OutputOpt = None,
) -> None:
    """Check only what a change introduced (working tree vs HEAD by default)."""
    root = Path.cwd()
    if bool(paths) != files:
        typer.echo("seamscan: give file paths together with --files", err=True)
        raise typer.Exit(code=2)
    try:
        limit: list[str] = []
        if paths:
            relative = _repo_relative(root, paths, root)
            outside = [str(p) for p, r in zip(paths, relative, strict=True) if r is None]
            limit = [r for r in relative if r is not None]
            unknown = [*outside, *unknown_paths(root, limit)]
            if unknown:
                typer.echo(
                    f"seamscan: not a tracked or untracked file in this repository: "
                    f"{', '.join(unknown)}",
                    err=True,
                )
                raise typer.Exit(code=2)
        change: ChangeSet = read_changeset(root, base=base, staged=staged, paths=limit)
    except GitError as exc:
        typer.echo(f"seamscan: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    _emit(_scan_change(root, change), fmt, output)


hook_app = typer.Typer(no_args_is_help=True, help="Adapters for coding-agent hooks.")
app.add_typer(hook_app, name="hook")


class _HookSetupError(RuntimeError):
    pass


def _claude_hook(raw: str) -> str | None:
    plan = read_input(raw)
    cwd = Path(plan.cwd)
    if not cwd.is_dir():
        raise _HookSetupError(f"cwd {plan.cwd} is not a directory")
    root = repo_root(cwd)
    if isinstance(plan, EditCheck):
        inside = [r for r in _repo_relative(root, plan.paths, cwd) if r is not None]
        # Files git ignores are out of scope, as they are for every other scan.
        ignored: set[str] = set(unknown_paths(root, inside)) if inside else set()
        limit = [p for p in inside if p not in ignored]
        if not limit:
            return None
        change = read_changeset(root, paths=limit)
    else:
        change = read_changeset(root)
    return respond(plan, _scan_change(root, change).verdict)


@hook_app.command("claude")
def hook_claude() -> None:
    """Claude Code hook: hook JSON on stdin, hook response on stdout (spec §11.4).

    Errors exit 1, never 2: Claude Code treats exit 2 from a Stop hook as "keep going",
    and a broken scanner must never trap the agent.
    """
    try:
        response = _claude_hook(sys.stdin.read())
    except (HookInputError, GitError, _HookSetupError) as exc:
        typer.echo(f"seamscan hook: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    except typer.Exit as exc:
        # The run already said why on stderr (e.g. a bad seamscan.toml); only its exit
        # code must change, since 2 would block.
        typer.echo(f"seamscan hook: scan stopped with exit code {exc.exit_code}", err=True)
        raise typer.Exit(code=1) from exc
    except Exception as exc:  # noqa: BLE001 - reported on stderr; the agent must go on
        typer.echo(f"seamscan hook: internal error: {type(exc).__name__}: {exc}", err=True)
        typer.echo(traceback.format_exc(), err=True)
        raise typer.Exit(code=1) from exc
    if response is not None:
        sys.stdout.write(response + "\n")


@app.command("rules")
def list_rules(
    as_json: Annotated[bool, typer.Option("--json", help="Machine-readable output")] = False,
) -> None:
    """List the rules with their severity, confidence and languages."""
    metas = [r.meta for r in RULES]
    sys.stdout.write(render_rule_json(metas) if as_json else render_rule_table(metas))


@app.command()
def explain(rule_id: Annotated[str, typer.Argument(help="A rule id, e.g. SC-CODE-001")]) -> None:
    """Print a rule's page: what it finds, why it matters, how to fix it."""
    wanted = rule_id.upper()
    ids = sorted(r.meta.id for r in RULES)
    if wanted not in ids:
        close = difflib.get_close_matches(wanted, ids, n=3)
        hint = f"did you mean {', '.join(close)}? " if close else ""
        typer.echo(f"seamscan: unknown rule {rule_id}; {hint}`seamscan rules` lists them", err=True)
        raise typer.Exit(code=2)
    # The pages ship inside the package, so this works from an installed wheel.
    sys.stdout.write((package_files("seamscan.rules") / "docs" / f"{wanted}.md").read_text())


def _show_version(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def _root(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            help="Show version and exit",
            callback=_show_version,
            is_eager=True,  # runs before Typer insists on a subcommand
        ),
    ] = False,
) -> None:
    """Static checks for the failures AI coding tools ship. See docs/SPEC.md."""


def main() -> None:
    app()
