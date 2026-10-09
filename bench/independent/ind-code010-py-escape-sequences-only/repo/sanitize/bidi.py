import re

BIDI = re.compile("[\u202a-\u202e\u2066-\u2069]")
ZW = "\u200b\u200c\u200d"


def strip_invisible(text: str) -> str:
    return BIDI.sub("", text).replace(ZW, "")
