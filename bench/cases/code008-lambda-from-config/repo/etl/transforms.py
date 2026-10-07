import yaml


def build_transforms(config_path: str) -> dict:
    with open(config_path) as fh:
        config = yaml.safe_load(fh)
    transforms = {}
    for column, expr in config["transforms"].items():
        transforms[column] = eval(f"lambda x: {expr}")
    return transforms
