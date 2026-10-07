import pickle

from app.snapshots import deep_copy


def test_deep_copy_matches_a_pickle_round_trip(tmp_path):
    value = {"a": [1, 2]}
    path = tmp_path / "v.pkl"
    path.write_bytes(pickle.dumps(value))
    assert deep_copy(value) == pickle.loads(path.read_bytes())
