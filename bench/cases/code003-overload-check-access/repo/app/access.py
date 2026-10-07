from typing import overload

from .models import Document, User


@overload
def check_access(user: User, doc: Document) -> bool: ...
@overload
def check_access(user: User, doc: None) -> None: ...


def check_access(user, doc):
    if doc is None:
        return None
    return doc.owner_id == user.id or user.is_admin
