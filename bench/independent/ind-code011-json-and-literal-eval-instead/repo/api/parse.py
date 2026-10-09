import ast
import json
from flask import request


def body():
    return json.loads(request.data)


def legacy_param():
    return ast.literal_eval(request.args.get("filter", "{}"))
