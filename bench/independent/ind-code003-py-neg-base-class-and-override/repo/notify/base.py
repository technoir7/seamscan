from typing import overload


class BaseNotifier:
    def send(self, user, message):
        raise NotImplementedError


class Notifier:
    def validate(self, message):
        raise NotImplementedError


class EmailNotifier(Notifier):
    def validate(self, message):
        return bool(message.strip())


@overload
def check_access(user: str, doc: str) -> bool: ...
@overload
def check_access(user: int, doc: int) -> bool: ...
def check_access(user, doc):
    return user == doc


class Money:
    def __eq__(self, other):
        return NotImplemented
