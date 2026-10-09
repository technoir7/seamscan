import json


def load_settings(path: str):
    with open(path) as f:
        try:
            return json.load(f)
        except:
            return None
