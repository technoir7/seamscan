import pickle
from django.conf import settings


def load_model():
    with open(settings.MODEL_PATH, "rb") as f:
        return pickle.load(f)
