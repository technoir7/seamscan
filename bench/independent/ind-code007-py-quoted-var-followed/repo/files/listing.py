import os
import shlex


def list_dir(p: str) -> None:
    safe = shlex.quote(p)
    os.system(f"ls -la {safe}")
