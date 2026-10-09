from flask import Flask, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from models import Task, db

app = Flask(__name__)


@app.post("/tasks")
@jwt_required()
def create_task():
    t = Task(title=request.json["title"], owner_id=get_jwt_identity())
    db.session.add(t)
    db.session.commit()
    return jsonify(id=t.id), 201
