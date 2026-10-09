import os


def secret() -> str:
    return os.environ["JWT_SECRET"]
