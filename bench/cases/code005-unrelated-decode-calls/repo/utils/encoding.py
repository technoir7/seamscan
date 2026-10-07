import base64
import codecs
import json


def parse_cookie(raw: bytes) -> dict:
    text = raw.decode("utf-8")
    payload = base64.urlsafe_b64decode(text.split(".")[1] + "==")
    return json.JSONDecoder().decode(payload.decode())


def rot13(s: str) -> str:
    return codecs.decode(s, "rot13")
