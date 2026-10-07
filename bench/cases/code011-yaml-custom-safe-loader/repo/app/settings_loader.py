import os

import yaml

Loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


class EnvLoader(yaml.SafeLoader):
    """SafeLoader plus an !env tag for values read from the environment."""


def _env_constructor(loader, node):
    return os.environ.get(loader.construct_scalar(node), "")


EnvLoader.add_constructor("!env", _env_constructor)


def load_fast(text: str) -> dict:
    return yaml.load(text, Loader=Loader)


def load_with_env(stream) -> dict:
    return yaml.load(stream, Loader=EnvLoader)
