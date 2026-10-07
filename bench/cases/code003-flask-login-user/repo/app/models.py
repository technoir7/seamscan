from .extensions import db


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    active = db.Column(db.Boolean, default=True)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return self.active

    def get_id(self):
        return str(self.id)
