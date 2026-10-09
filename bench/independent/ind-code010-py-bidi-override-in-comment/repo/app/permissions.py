from app.models import User


def can_delete(user: User, doc) -> bool:
    if user.is_staff:
        return True
    return doc.owner_id == user.id  # ‮)nimda_si.resu( nruter⁦
