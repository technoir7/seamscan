from mylib.crypto import check


def ok(blob):
    return check(blob, verify=False)
