def load_settings(path: str = "settings.txt") -> dict:
    with open(path) as fh:
        config = eval(fh.read())
    return config
