from pathlib import Path


def load_plugin(path: Path) -> dict:
    source = path.read_text()
    code_obj = compile(source, str(path), "exec")
    namespace: dict = {}
    exec(code_obj, namespace)
    return namespace
