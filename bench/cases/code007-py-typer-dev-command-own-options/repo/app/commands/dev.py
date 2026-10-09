"""Run a development server from the command line."""

import subprocess

import typer

app = typer.Typer()


@app.callback(invoke_without_command=True)
def serve(
    port: int = typer.Option(8000, "--port", "-p", help="Port to listen on"),
    host: str = typer.Option("localhost", "--host", "-h", help="Interface to bind"),
    *,
    reload: bool = typer.Option(True, help="Reload on code changes"),
) -> None:
    """Start uvicorn with auto-reload."""
    typer.echo("Starting the development server...")
    cmd_line = f"uvicorn app.main:app --port={port} --host={host} {'--reload' if reload else ''}"
    subprocess.call(cmd_line, shell=True)
