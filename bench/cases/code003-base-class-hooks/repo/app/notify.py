class BaseNotifier:
    """Subclasses deliver a message over one channel."""

    def send(self, user, message: str) -> None:
        raise NotImplementedError

    def validate_recipient(self, user) -> bool:
        return True


class EmailNotifier(BaseNotifier):
    def __init__(self, mailer) -> None:
        self.mailer = mailer

    def send(self, user, message: str) -> None:
        self.mailer.send(user.email, message)

    def validate_recipient(self, user) -> bool:
        return bool(user.email) and user.email_verified
