from sync.merge import merge_records


def test_merge_prefers_newer():
    a = {"id": 1, "v": 1, "ts": 1}
    b = {"id": 1, "v": 2, "ts": 2}
    assert merge_records(a, b)["v"] == 2
