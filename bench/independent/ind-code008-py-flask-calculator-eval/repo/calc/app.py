import math
from flask import Flask, request, jsonify

app = Flask(__name__)


@app.get("/calc")
def calc():
    expr = request.args.get("expr", "0")
    result = eval(expr, {"math": math})
    return jsonify(result=result)
