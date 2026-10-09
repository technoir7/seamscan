import re

BIDI = re.compile("[‪-‮⁦-⁩]")
ZW = "​‌‍"


def strip_invisible(text: str) -> str:
    return BIDI.sub("", text).replace(ZW, "")
