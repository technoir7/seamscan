import json


def load(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        pass
