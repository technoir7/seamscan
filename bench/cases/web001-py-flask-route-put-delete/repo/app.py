from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///blog.db"
db = SQLAlchemy(app)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)


@app.route("/posts", methods=["GET"])
def list_posts():
    return jsonify([{"id": p.id, "title": p.title} for p in Post.query.all()])


@app.route("/posts/<int:post_id>", methods=["PUT", "DELETE"])
def change_post(post_id):
    post = Post.query.get_or_404(post_id)
    if request.method == "DELETE":
        db.session.delete(post)
        db.session.commit()
        return "", 204
    data = request.get_json()
    post.title = data.get("title", post.title)
    post.body = data.get("body", post.body)
    db.session.commit()
    return jsonify({"id": post.id})
