class User:
    def __init__(self, name):
        self.name = name

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False


def get_author(post):
    pass


def on_checkbox_toggled(event):
    pass
