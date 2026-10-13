import subprocess
from pathlib import Path

import pytest

from seamscan.workspace.files import collect


def _write(root: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


@pytest.mark.parametrize("use_git", [True, False])
def test_a_committed_virtualenv_under_any_name_is_not_analyzed(tmp_path: Path, use_git: bool):
    _write(
        tmp_path,
        {
            "app/views.py": "x = 1\n",
            "djangoenv/pyvenv.cfg": "home = /usr/bin\n",
            "djangoenv/Lib/site-packages/requests/api.py": "x = 1\n",
            "djangoenv/Scripts/activate_this.py": "x = 1\n",
        },
    )
    if use_git:  # git lists untracked files too, so the walk is not what's tested
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    fileset = collect(tmp_path, use_git=use_git)
    assert [f.path for f in fileset.files] == ["app/views.py"]
    assert ("djangoenv/", "virtualenv") in fileset.skipped


def test_installed_packages_are_not_analyzed_without_a_pyvenv_cfg(tmp_path: Path):
    _write(
        tmp_path,
        {
            "app/views.py": "x = 1\n",
            "pyenv/lib/python3.12/site-packages/flask/app.py": "x = 1\n",
        },
    )
    assert [f.path for f in collect(tmp_path, use_git=False).files] == ["app/views.py"]


def test_vites_prebundled_dependencies_are_not_analyzed(tmp_path: Path):
    _write(
        tmp_path,
        {
            "src/App.jsx": "export default 1;\n",
            "Client/.vite/deps_temp_2184bafc/react-dom_client.js": "export default 1;\n",
        },
    )
    assert [f.path for f in collect(tmp_path, use_git=False).files] == ["src/App.jsx"]
