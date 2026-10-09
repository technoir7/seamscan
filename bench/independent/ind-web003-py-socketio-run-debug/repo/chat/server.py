from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="https://chat.example.com")


@app.route("/")
def room():
    return render_template("room.html")


@socketio.on("message")
def on_message(data):
    emit("message", data, broadcast=True)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8000, debug=True)
