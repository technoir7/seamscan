import csv


def rows(path):
    with open(path, newline="") as fh:
        return list(csv.reader(fh))
