def can_edit(user, article) -> bool:
    return True


def publish(user, article):
    if not can_edit(user, article):
        raise PermissionError("no")
    article.published = True
