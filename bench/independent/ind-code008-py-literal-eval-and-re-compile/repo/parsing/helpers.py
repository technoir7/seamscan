import ast
import re
from re import compile as rcompile


def parse_dict(raw: str) -> dict:
    return ast.literal_eval(raw)


def make_matcher(user_pattern: str):
    return re.compile(user_pattern)


def make_other(user_pattern: str):
    return rcompile(user_pattern, re.I)
