from bench.case import changeset_between
from seamscan.model import WHOLE_FILE, SourceFile


def test_inserted_and_replaced_lines_count_as_added():
    base = (SourceFile("a.py", "one\ntwo\nthree\n"),)
    head = (SourceFile("a.py", "one\nTWO\ninserted\nthree\n"), SourceFile("new.py", "x\n"))
    change = changeset_between(base, head)
    assert change.added["a.py"] == ((2, 3),)
    assert change.added["new.py"] == (WHOLE_FILE,)


def test_unchanged_file_has_no_entry():
    files = (SourceFile("a.py", "same\n"),)
    assert "a.py" not in changeset_between(files, files).added
