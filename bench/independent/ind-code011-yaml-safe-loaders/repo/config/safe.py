import yaml


def a(fh):
    return yaml.safe_load(fh)


def b(text):
    return yaml.load(text, Loader=yaml.CSafeLoader)


def c(text):
    return yaml.load(text, yaml.SafeLoader)
