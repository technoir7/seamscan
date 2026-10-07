import csv


def export(rows, path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        csv.writer(f).writerows(rows)
