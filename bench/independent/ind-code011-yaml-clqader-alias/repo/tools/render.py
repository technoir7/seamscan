import sys
from yaml import load, CLoader as Loader


def parse(text):
    return load(text, Loader=Loader)


if __name__ == "__main__":
    print(parse(sys.stdin.read()))
