import tomllib


def load(path):
    try:
        with open(path, "rb") as f:
            cfg = tomllib.load(f)
    except Exception:
        cfg = {"debug": False}
    return cfg
