import os
import pickle
from pathlib import Path

import torch
import yaml

HERE = Path(__file__).resolve().parent
MODEL_PATH = HERE / "artifacts" / "classifier.pkl"


def load_classifier():
    with MODEL_PATH.open("rb") as fh:
        return pickle.load(fh)


def load_vectorizer():
    with open("artifacts/vectorizer.pkl", "rb") as fh:
        return pickle.load(fh)


def load_weights():
    path = os.path.join(os.path.dirname(__file__), "artifacts", "weights.pt")
    return torch.load(path, weights_only=False)


def load_settings():
    with open(HERE / "settings.yaml") as fh:
        return yaml.load(fh, Loader=yaml.FullLoader)
