import sys


def load_config(path):
    with open(path) as fh:
        config = eval(fh.read())
    return config


if __name__ == "__main__":
    print(load_config(sys.argv[1]))
