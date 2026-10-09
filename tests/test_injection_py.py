"""SC-CODE-007 on Python shapes the benchmark cases don't pin down."""

from seamscan.analysis import analyze
from seamscan.model import SourceFile


def shell_lines(src: str, path: str = "app/commands/dev.py") -> list[int]:
    found = analyze([SourceFile(path, src)]).findings
    return [f.location.start_line for f in found if f.rule_id == "SC-CODE-007"]


_TYPER = """\
import subprocess
import typer

app = typer.Typer()


@app.callback(invoke_without_command=True)
def serve(host: str = typer.Option("localhost", "--host"), port: int = 8000):
    cmd = f"uvicorn app.main:app --host={host} --port={port}"
    subprocess.call(cmd, shell=True)
"""


def test_a_command_line_tools_own_options_are_not_attacker_input():
    # Whoever runs `dev serve --host ...` already has a shell; the values are theirs.
    assert shell_lines(_TYPER) == []


def test_click_command_arguments_are_the_operators_own():
    src = (
        "import os\nimport click\n\n\n@click.command()\n@click.argument('name')\n"
        "def restart(name):\n    os.system('systemctl restart ' + name)\n"
    )
    assert shell_lines(src) == []


def test_the_same_parameter_outside_a_command_is_still_reported():
    src = _TYPER.replace("@app.callback(invoke_without_command=True)\n", "")
    assert shell_lines(src) == [9]


def test_other_values_inside_a_command_are_still_judged():
    src = (
        "import subprocess\nimport requests\nimport typer\n\napp = typer.Typer()\n\n\n"
        "@app.command()\ndef fetch(url: str):\n    ref = requests.get(url).text\n"
        "    subprocess.run(f'git checkout {ref}', shell=True)\n"
    )
    assert shell_lines(src) == [11]
