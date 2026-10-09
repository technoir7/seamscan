from pathlib import Path


def run_hook(path: Path, env: dict):
    source = path.read_text()
    code_obj = compile(source, str(path), "exec")
    exec(code_obj, env)
    return env
