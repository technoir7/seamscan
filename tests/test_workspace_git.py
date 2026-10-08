import subprocess
from pathlib import Path

import pytest

from seamscan.workspace.git import GitError, read_changeset, read_file_at


def test_outside_a_repository_gives_one_clear_line(tmp_path):
    with pytest.raises(GitError) as err:
        read_changeset(tmp_path)
    message = str(err.value)
    assert "not inside a git repository" in message
    assert "seamscan audit" in message
    assert "\n" not in message


def git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
        cwd=root,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "a.txt").write_text("committed\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "one")
    (tmp_path / "sub" / "a.txt").write_text("working tree\n")
    return tmp_path


def test_reads_the_committed_text_not_the_working_tree(repo: Path):
    assert read_file_at(repo, "HEAD", "sub/a.txt") == "committed\n"


def test_path_is_relative_to_the_given_root_even_below_the_repository_top(repo: Path):
    assert read_file_at(repo / "sub", "HEAD", "a.txt") == "committed\n"


def test_a_file_missing_at_the_ref_is_none(repo: Path):
    assert read_file_at(repo, "HEAD", "sub/nope.txt") is None


def test_an_unknown_ref_is_an_error_naming_it(repo: Path):
    with pytest.raises(GitError) as err:
        read_file_at(repo, "no-such-branch", "sub/a.txt")
    assert "no-such-branch" in str(err.value)


def test_a_ref_that_looks_like_an_option_is_refused(repo: Path):
    with pytest.raises(GitError):
        read_file_at(repo, "--output=/tmp/x", "sub/a.txt")


def test_outside_a_repository_is_an_error(tmp_path: Path):
    with pytest.raises(GitError):
        read_file_at(tmp_path, "HEAD", "a.txt")
