import pickle
import yaml


def test_roundtrip(tmp_path):
    p = tmp_path / "x.pkl"
    p.write_bytes(pickle.dumps({"a": 1}))
    assert pickle.loads(p.read_bytes()) == {"a": 1}
    cfg = tmp_path / "c.yaml"
    cfg.write_text("a: 1")
    assert yaml.load(cfg.read_text(), Loader=yaml.FullLoader) == {"a": 1}
