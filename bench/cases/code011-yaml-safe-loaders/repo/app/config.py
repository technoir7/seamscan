import yaml
from yaml import CSafeLoader


def load_config(path: str) -> dict:
    with open(path) as fh:
        return yaml.safe_load(fh)


def parse(text: str) -> dict:
    return yaml.load(text, Loader=yaml.SafeLoader)


def parse_fast(text: str) -> dict:
    return yaml.load(text, Loader=CSafeLoader)


def parse_positional(text: str) -> dict:
    return yaml.load(text, yaml.SafeLoader)


def parse_strings_only(text: str) -> dict:
    return yaml.load(text, Loader=yaml.BaseLoader)


def parse_many(text: str) -> list:
    return list(yaml.safe_load_all(text))
