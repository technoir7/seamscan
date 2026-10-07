import ast
import json

from flask import Flask, request
from itsdangerous import URLSafeTimedSerializer

app = Flask(__name__)
serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"], salt="email-confirm")


@app.post("/webhook")
def webhook():
    event = json.loads(request.data)
    return {"type": event["type"]}


@app.get("/confirm/<token>")
def confirm(token: str):
    email = serializer.loads(token, max_age=3600)
    return {"email": email}


def parse_tuple(text: str):
    return ast.literal_eval(text)
