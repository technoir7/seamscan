import yaml

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


def read_manifest(stream):
    return yaml.load(stream, Loader=Loader)


def read_all(stream):
    return list(yaml.load_all(stream, Loader))
