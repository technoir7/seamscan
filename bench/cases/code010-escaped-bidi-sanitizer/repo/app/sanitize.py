import re

# Strip U+202A..U+202E and U+2066..U+2069 (Trojan Source, CVE-2021-42574).
BIDI_CONTROLS = re.compile("[\u202a-\u202e\u2066-\u2069\u200e\u200f]")


def clean(text: str) -> str:
    return BIDI_CONTROLS.sub("", text)
