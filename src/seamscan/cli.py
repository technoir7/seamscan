"""Composition root: the only place that wires I/O to the pure core (spec §5.2, §11.1)."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from seamscan import __version__
from seamscan.analysis import Analysis, analyze
from seamscan.model import ChangeSet, SourceFile
from seamscan.policy.verdict import Policy, Verdict, decide
from seamscan.report.json import render_json
from seamscan.report.terminal import render_terminal
from seamscan.workspace.files import collect
from seamscan.workspace.git import GitError, read_changeset

app = typer.Typer(add_completion=False, no_args_is_help=True)


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
