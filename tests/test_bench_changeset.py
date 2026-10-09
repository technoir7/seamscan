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


def test_files_the_case_gitignores_are_not_read_as_in_the_cli(tmp_path):
    from bench.case import case_files, load_case

    directory = tmp_path / "c1"
    (directory / "repo").mkdir(parents=True)
    (directory / "repo" / ".gitignore").write_text(".env\n")
    (directory / "repo" / ".env").write_text("SECRET=1\n")
    (directory / "repo" / "app.py").write_text("x = 1\n")
    (directory / "case.toml").write_text(
        'id = "c1"\ndescription = "d"\nsplit = "dev"\n[provenance]\nsource = "original"\n'
    )
    assert {f.path for f in case_files(load_case(directory))} == {".gitignore", "app.py"}
