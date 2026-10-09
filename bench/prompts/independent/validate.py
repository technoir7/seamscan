"""Format check for independent cases. Runs no detection rule."""

import sys
from pathlib import Path

sys.path.insert(0, "/Users/aaronfung/Documents/code/seamscan")
from bench.case import CaseError, case_files, case_registry, load_case  # noqa: E402

root = Path(sys.argv[1])
bad = 0
for d in sorted(p for p in root.iterdir() if p.is_dir()):
    try:
        case = load_case(d)
        if case.split != "independent" or not case.id.startswith("ind-"):
            raise CaseError("split must be 'independent' and id must start with 'ind-'")
        files = {f.path: f.text.splitlines() for f in case_files(case)}
        case_registry(case)
        if not case.expected and not case.forbidden:
            raise CaseError("no [[expected]] and no [[forbidden]]")
        for e in case.expected:
            lines = files.get(e.path)
            if lines is None:
                raise CaseError(f"expected path {e.path} is not a file seamscan reads in repo/")
            if not 1 <= e.line <= len(lines):
                raise CaseError(f"{e.path}:{e.line} is past the end of the file")
            print(f"  {d.name}: {e.rule} {e.path}:{e.line}  | {lines[e.line - 1].strip()[:100]}")
    except Exception as exc:  # report every case's problem, then fail
        bad += 1
        print(f"ERROR {d.name}: {exc}")
print(f"\n{bad} case(s) with errors")
sys.exit(1 if bad else 0)
