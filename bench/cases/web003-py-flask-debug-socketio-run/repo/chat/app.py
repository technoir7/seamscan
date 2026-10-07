from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins=["http://localhost:5173"])


@app.get("/")
def index():
    return render_template("index.html")


@socketio.on("message")
def on_message(data):
    emit("message", data, broadcast=True)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
