import os


def folder_size(path: str) -> str:
    return os.popen(f"du -sh {path}").read().split()[0]
