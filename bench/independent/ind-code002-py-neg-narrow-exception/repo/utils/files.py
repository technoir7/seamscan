import os


def remove_quietly(path: str) -> None:
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def read_int(s: str):
    try:
        return int(s)
    except (ValueError, TypeError):
        return None
