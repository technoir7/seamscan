"""Composition root: the only place that wires I/O to the pure core (spec §5.2, §11.1)."""

from __future__ import annotations

import sys
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from seamscan import __version__
from seamscan.analysis import analyze
from seamscan.model import ChangeSet, Finding
from seamscan.policy.verdict import Policy, decide
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


def _emit(findings: tuple[Finding, ...], fmt: Format, output: Path | None) -> None:
    verdict = decide(findings, Policy())
    if fmt is Format.json:
        text = render_json(findings, verdict, __version__)
    else:
        text = render_terminal(findings, verdict)
    if output:
        output.write_text(text)
    else:
        sys.stdout.write(text)
    raise typer.Exit(code=verdict.exit_code)


@app.command()
def audit(
    path: Annotated[Path, typer.Argument(help="Repository root")] = Path("."),
    fmt: FormatOpt = Format.terminal,
    output: OutputOpt = None,
) -> None:
    """Check a whole repository."""
    fileset = collect(path.resolve())
    _emit(analyze(fileset.files), fmt, output)


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
    _emit(analyze(changed, change=change), fmt, output)


@app.callback()
def _root(
    version: Annotated[bool, typer.Option("--version", help="Show version and exit")] = False,
) -> None:
    if version:
        typer.echo(__version__)
        raise typer.Exit()


def main() -> None:
    app()
