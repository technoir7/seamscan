import os
import yaml

Loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


class EnvLoader(yaml.SafeLoader):
    pass


def with_env(text):
    return yaml.load(text, Loader=EnvLoader)


def plain(text):
    return yaml.load(text, Loader=Loader)
