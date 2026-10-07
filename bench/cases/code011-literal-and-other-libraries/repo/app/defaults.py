import shelve

import numpy as np
import yaml

DEFAULTS = yaml.load("retries: 3\ntimeout: 10\n", Loader=yaml.Loader)


def remember(user_id: str, prefs: dict) -> None:
    with shelve.open("prefs.db") as db:
        db[user_id] = prefs


def embeddings(path: str):
    return np.load(path)


def warm(model, path: str):
    model.load(path)
    return model
