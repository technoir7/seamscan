"""Spec §11.1 and §11.4 through the CLI, on a real temporary git repository."""

import json
import subprocess
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

import seamscan.cli
from seamscan.cli import app

runner = CliRunner()

BAD = "import requests\nrequests.get(u, verify=False)\n"  # SC-CODE-001, blocking
NOTE = "def f():\n    try:\n        g()\n    except Exception:\n        pass\n"  # non-blocking


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.email", "t@example.com")
    git(root, "config", "user.name", "t")
    (root / "a.py").write_text("x = 1\n")
    (root / "b.py").write_text("y = 2\n")
    (root / ".gitignore").write_text("ignored.py\n")
    git(root, "add", ".")
    git(root, "commit", "-qm", "init")
    monkeypatch.chdir(root)
    return root


def rule_paths(stdout: str) -> list[tuple[str, str]]:
    return [(f["rule_id"], f["location"]["path"]) for f in json.loads(stdout)["findings"]]


# --- scan --files ----------------------------------------------------------------------


def test_files_limits_the_scan_to_the_named_files(repo: Path):
    (repo / "a.py").write_text("x = 1\n" + BAD)
    (repo / "b.py").write_text("y = 2\n" + BAD)
    result = runner.invoke(app, ["scan", "--files", "a.py", "--format", "json"])
    assert result.exit_code == 1
    assert rule_paths(result.stdout) == [("SC-CODE-001", "a.py")]


def test_files_counts_only_added_lines(repo: Path):
    (repo / "a.py").write_text(BAD)
    git(repo, "commit", "-qam", "debt")
    (repo / "a.py").write_text(BAD + "z = 3\n")
    result = runner.invoke(app, ["scan", "--files", "a.py", "--format", "json"])
    assert result.exit_code == 0, result.stdout
    assert rule_paths(result.stdout) == []


def test_files_treats_an_untracked_file_as_wholly_new(repo: Path):
    (repo / "new.py").write_text(BAD)
    result = runner.invoke(app, ["scan", "--files", "new.py", "b.py", "--format", "json"])
    assert result.exit_code == 1
    assert rule_paths(result.stdout) == [("SC-CODE-001", "new.py")]


@pytest.mark.parametrize("path", ["missing.py", "ignored.py", "../elsewhere.py"])
def test_files_rejects_a_path_git_doesnt_know(repo: Path, path: str):
    (repo / "ignored.py").write_text(BAD)
    result = runner.invoke(app, ["scan", "--files", path])
    assert result.exit_code == 2
    assert path.removeprefix("../") in result.stderr


def test_paths_without_files_flag_and_files_flag_without_paths_are_usage_errors(repo: Path):
    assert runner.invoke(app, ["scan", "a.py"]).exit_code == 2
    assert runner.invoke(app, ["scan", "--files"]).exit_code == 2


# --- agent format ----------------------------------------------------------------------


def test_scan_agent_format(repo: Path):
    (repo / "a.py").write_text("x = 1\n" + BAD)
    result = runner.invoke(app, ["scan", "--format", "agent"])
    assert result.exit_code == 1
    assert result.stdout.splitlines() == [
        "seamscan: 1 blocking finding(s)",
        "a.py:3 [SC-CODE-001] `requests.get` called with verify=False"
        " → seamscan explain SC-CODE-001",
    ]


# --- hook claude -------------------------------------------------------------------------


def hook(payload: dict[str, object] | str) -> object:
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    return runner.invoke(app, ["hook", "claude"], input=raw)


def edit(repo: Path, path: str, cwd: Path | None = None) -> dict[str, object]:
    return {
        "session_id": "s",
        "cwd": str(cwd or repo),
        "hook_event_name": "PostToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": str(repo / path), "old_string": "", "new_string": ""},
        "tool_response": {"filePath": str(repo / path)},
    }


def stop(repo: Path, active: bool = False) -> dict[str, object]:
    return {
        "session_id": "s",
        "cwd": str(repo),
        "hook_event_name": "Stop",
        "stop_hook_active": active,
    }


def test_hook_post_tool_use_reports_blocking_findings_in_the_edited_file(repo: Path):
    (repo / "a.py").write_text("x = 1\n" + BAD)
    (repo / "b.py").write_text("y = 2\n" + BAD)  # dirty too, but not this edit
    result = hook(edit(repo, "a.py"))
    assert result.exit_code == 0
    context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "a.py:3 [SC-CODE-001]" in context
    assert "b.py" not in context


def test_hook_post_tool_use_is_silent_without_blocking_findings(repo: Path):
    (repo / "a.py").write_text("x = 1\n" + NOTE)
    result = hook(edit(repo, "a.py"))
    assert (result.exit_code, result.stdout) == (0, "")


def test_hook_post_tool_use_on_a_new_file_from_a_subdirectory(repo: Path):
    (repo / "pkg").mkdir()
    (repo / "pkg" / "new.py").write_text(BAD)
    result = hook(edit(repo, "pkg/new.py", cwd=repo / "pkg"))
    assert result.exit_code == 0
    assert "pkg/new.py:2 [SC-CODE-001]" in result.stdout


@pytest.mark.parametrize("path", ["ignored.py", "../outside.py"])
def test_hook_ignores_files_outside_the_repository_or_ignored_by_git(repo: Path, path: str):
    (repo / path).write_text(BAD)
    result = hook(edit(repo, path))
    assert (result.exit_code, result.stdout) == (0, "")


def test_hook_stop_blocks_on_blocking_findings_in_the_working_tree(repo: Path):
    (repo / "b.py").write_text("y = 2\n" + BAD)
    result = hook(stop(repo))
    assert result.exit_code == 0
    doc = json.loads(result.stdout)
    assert doc["decision"] == "block"
    assert "b.py:3 [SC-CODE-001]" in doc["reason"]


def test_hook_stop_when_already_continued_only_tells_the_user(repo: Path):
    (repo / "b.py").write_text("y = 2\n" + BAD)
    result = hook(stop(repo, active=True))
    assert result.exit_code == 0
    assert set(json.loads(result.stdout)) == {"systemMessage"}


def test_hook_stop_is_silent_on_a_clean_tree(repo: Path):
    result = hook(stop(repo))
    assert (result.exit_code, result.stdout) == (0, "")


# Claude Code treats exit 2 as "block" on Stop: a broken hook must exit with another code.
NON_BLOCKING_ERROR = 1


@pytest.mark.parametrize("raw", ["", "{not json", '{"hook_event_name": "Stop"}'])
def test_hook_malformed_input_is_a_non_blocking_error(repo: Path, raw: str):
    result = hook(raw)
    assert result.exit_code == NON_BLOCKING_ERROR
    assert result.stdout == ""
    assert result.stderr.startswith("seamscan hook:")


def test_hook_outside_a_git_repository_is_a_non_blocking_error(tmp_path: Path):
    result = hook(stop(tmp_path))
    assert result.exit_code == NON_BLOCKING_ERROR
    assert result.stdout == ""
    assert "not inside a git repository" in result.stderr


def test_hook_crash_is_a_non_blocking_error(repo: Path, monkeypatch: pytest.MonkeyPatch):
    def boom(*_: object, **__: object) -> object:
        raise RuntimeError("kaboom")

    monkeypatch.setattr(seamscan.cli, "collect", boom)
    result = hook(stop(repo))
    assert result.exit_code == NON_BLOCKING_ERROR
    assert result.stdout == ""
    assert "kaboom" in result.stderr


def test_hook_turns_a_usage_error_exit_into_a_non_blocking_one(
    repo: Path, monkeypatch: pytest.MonkeyPatch
):
    # A bad seamscan.toml or baseline makes the run exit 2, which Claude Code reads as
    # "block" on Stop.
    def bad_config(*_: object, **__: object) -> object:
        raise typer.Exit(code=2)

    monkeypatch.setattr(seamscan.cli, "_run", bad_config)
    result = hook(stop(repo))
    assert result.exit_code == NON_BLOCKING_ERROR
    assert result.stdout == ""
    assert "exit code 2" in result.stderr
