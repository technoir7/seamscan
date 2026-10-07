"""Spec §5.3: the pure core never reaches I/O, and lower layers never import higher ones."""

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src" / "seamscan"

PURE_LAYERS = ("model", "parse", "facts", "rules", "policy", "report", "analysis")
IO_MODULES = {"subprocess", "urllib", "socket", "http", "requests", "httpx", "shutil"}
IO_PACKAGES = {"seamscan.workspace", "seamscan.supply", "seamscan.cli"}

# A layer may import only the layers listed for it (plus itself and stdlib).
ALLOWED = {
    "model": set(),
    "parse": {"model"},
    "facts": {"model", "parse"},
    "rules": {"model", "parse", "facts"},
    "policy": {"model"},
    "report": {"model", "policy"},
    "analysis": {"model", "parse", "facts", "rules", "policy"},
}


def layer_of(path: Path) -> str:
    rel = path.relative_to(SRC).with_suffix("")
    return rel.parts[0]


def imports_of(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.append(node.module)
    return names


def pure_modules() -> list[Path]:
    return [p for p in SRC.rglob("*.py") if layer_of(p) in PURE_LAYERS]


def test_there_are_modules_to_check():
    assert pure_modules()


def test_pure_layers_do_no_io():
    violations = []
    for path in pure_modules():
        for name in imports_of(path):
            top = name.split(".")[0]
            if top in IO_MODULES or any(name.startswith(p) for p in IO_PACKAGES):
                violations.append(f"{path.relative_to(SRC)} imports {name}")
            if name == "os" or name.startswith("os."):
                violations.append(f"{path.relative_to(SRC)} imports {name} (env/filesystem)")
    assert not violations, "\n".join(violations)


def test_layers_only_import_downward():
    violations = []
    for path in pure_modules():
        layer = layer_of(path)
        for name in imports_of(path):
            if not name.startswith("seamscan."):
                continue
            target = name.removeprefix("seamscan.")
            target_layer = target.split(".")[0]
            if target_layer == layer:
                continue
            allowed = ALLOWED[layer]
            if target_layer not in allowed and target not in allowed:
                violations.append(f"{path.relative_to(SRC)} ({layer}) imports {name}")
    assert not violations, "\n".join(violations)
