import uuid

from flask import Flask, g, jsonify
from pymongo import MongoClient

app = Flask(__name__)
mongo = MongoClient("mongodb://localhost:27017").shop


@app.before_request
def tag_request():
    g.request_id = str(uuid.uuid4())


@app.route("/products/<pid>", methods=["DELETE"])
def remove_product(pid):
    result = mongo.products.delete_one({"_id": pid})
    return jsonify(deleted=result.deleted_count)
