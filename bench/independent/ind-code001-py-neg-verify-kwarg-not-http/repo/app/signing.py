import hashlib


def check(blob: bytes, digest: str, verify: bool = True) -> bool:
    return not verify or hashlib.sha256(blob).hexdigest() == digest


def preview(blob: bytes) -> bool:
    return check(blob, "", verify=False)
