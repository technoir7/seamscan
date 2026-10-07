"""SC-CODE-011 decisions the benchmark doesn't pin down one by one."""

from seamscan.analysis import analyze
from seamscan.model import Finding, SourceFile
from seamscan.rules.deserialize import RULES


def run(src: str, path: str = "app/x.py") -> tuple[Finding, ...]:
    return analyze([SourceFile(path, src)], rules=RULES).findings


def lines(src: str, path: str = "app/x.py") -> list[int]:
    return [f.location.start_line for f in run(src, path)]


def test_each_unsafe_loader_on_a_parameter():
    src = (
        "import pickle, _pickle, dill, marshal, jsonpickle, yaml\n"
        "def f(d):\n"
        "    pickle.loads(d)\n"
        "    _pickle.load(d)\n"
        "    dill.load(d)\n"
        "    marshal.load(d)\n"
        "    jsonpickle.loads(d)\n"
        "    yaml.full_load(d)\n"
        "    yaml.unsafe_load_all(d)\n"
        "    yaml.load(d)\n"
        "    yaml.load(d, yaml.UnsafeLoader)\n"
        "    yaml.load(stream=d, Loader=yaml.CLoader)\n"
    )
    assert lines(src) == list(range(3, 13))


def test_literal_input_and_safe_loaders_are_not_reported():
    src = (
        "import pickle, yaml\n"
        "from yaml import CSafeLoader as Fast\n"
        "A = pickle.loads(b'\\x80\\x04K\\x01.')\n"
        "def f(d):\n"
        "    yaml.load(d, Loader=Fast)\n"
        "    yaml.load(d, Loader=yaml.CBaseLoader)\n"
        "    yaml.load_all(d, yaml.SafeLoader)\n"
    )
    assert lines(src) == []


def test_torch_load_needs_an_explicit_weights_only_other_than_true():
    src = (
        "import torch\n"
        "def f(p, trust):\n"
        "    torch.load(p)\n"
        "    torch.load(p, weights_only=True)\n"
        "    torch.load(p, weights_only=False)\n"
        "    torch.load(p, weights_only=trust)\n"
    )
    assert lines(src) == [5, 6]


def test_files_opened_from_fixed_paths_are_not_reported():
    src = (
        "import gzip, os, pickle\n"
        "from pathlib import Path\n"
        "HERE = Path(__file__).resolve().parent\n"
        "def a():\n"
        "    with gzip.open(HERE / 'm.pkl.gz') as fh:\n"
        "        return pickle.load(fh)\n"
        "def b():\n"
        "    return pickle.loads((HERE / 'm.pkl').read_bytes())\n"
        "def c():\n"
        "    return pickle.load(open(str(Path('m.pkl')), 'rb'))\n"
    )
    assert lines(src) == []


def test_files_opened_from_other_paths_are_reported():
    src = (
        "import pickle\n"
        "def a(path):\n"
        "    with open(path, 'rb') as fh:\n"
        "        return pickle.load(fh)\n"
        "def b(name):\n"
        "    with open(f'/srv/uploads/{name}', 'rb') as fh:\n"
        "        return pickle.load(fh)\n"
    )
    assert lines(src) == [4, 7]


def test_with_binding_in_another_function_does_not_count():
    src = (
        "import pickle\n"
        "def a():\n"
        "    with open('fixed.pkl', 'rb') as fh:\n"
        "        return fh.read()\n"
        "def b(fh):\n"
        "    return pickle.load(fh)\n"
    )
    assert lines(src) == [6]


def test_test_files_are_skipped_and_the_message_names_the_call():
    src = "import pickle\ndef f(d):\n    return pickle.loads(d)\n"
    assert not run(src, "tests/test_x.py")
    (f,) = run(src)
    assert "pickle.loads" in f.message
