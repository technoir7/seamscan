ALLOWED_ROLES = {"admin", "owner"}​


def can_delete(user) -> bool:
    return user.role in ALLOWED_ROLES
