import pickle
from flask import Flask, request, jsonify
from serving.model import predict

app = Flask(__name__)


@app.post("/predict")
def predict_route():
    features = pickle.loads(request.data)
    return jsonify(score=predict(features))
