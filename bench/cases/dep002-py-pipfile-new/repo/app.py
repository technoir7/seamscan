from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")
    db.init_app(app)
    login_manager.init_app(app)

    from .routes import main

    app.register_blueprint(main)
    return app
