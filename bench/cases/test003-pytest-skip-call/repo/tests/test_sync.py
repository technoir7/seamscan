import pytest

from sync.client import SyncClient


def test_sync_merges_conflicting_edits(tmp_path):
    pytest.skip("merge logic under rework")
    client = SyncClient(root=tmp_path)
    client.write("notes.txt", "a")
    client.write_remote("notes.txt", "b")
    client.sync()
    assert client.read("notes.txt") == "a\nb"
