import ast
import json
from ast import literal_eval


def parse_tuple(raw: str) -> tuple:
    return ast.literal_eval(raw)


def parse_any(raw: str):
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return literal_eval(raw)
