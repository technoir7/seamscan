import pickle

from flask import Flask, jsonify, request

app = Flask(__name__)


@app.post("/predict")
def predict():
    features = pickle.loads(request.data)
    score = sum(features.get("weights", [])) / max(len(features), 1)
    return jsonify({"score": score})
