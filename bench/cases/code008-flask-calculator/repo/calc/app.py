from flask import Flask, jsonify, request

app = Flask(__name__)


@app.get("/calculate")
def calculate():
    expression = request.args.get("expr", "0")
    try:
        result = eval(expression)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"result": result})
