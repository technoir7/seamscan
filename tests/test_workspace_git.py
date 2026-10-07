import pytest

from seamscan.workspace.git import GitError, read_changeset


def test_outside_a_repository_gives_one_clear_line(tmp_path):
    with pytest.raises(GitError) as err:
        read_changeset(tmp_path)
    message = str(err.value)
    assert "not inside a git repository" in message
    assert "seamscan audit" in message
    assert "\n" not in message
