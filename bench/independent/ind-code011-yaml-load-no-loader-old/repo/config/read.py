import os
import yaml


def read_settings():
    path = os.environ["APP_SETTINGS"]
    with open(path) as fh:
        return yaml.load(fh)
