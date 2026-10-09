from app.db import db


def refund_credits(user_id: int, amount: int) -> None:
    try:
        db.session.execute(
            "UPDATE users SET credits = credits + :n WHERE id = :id", {"n": amount, "id": user_id}
        )
        db.session.commit()
    except Exception:  # TODO: handle this
        pass


def touch_last_seen(user_id: int) -> None:
    try:
        db.session.execute("UPDATE users SET seen = now() WHERE id = :id", {"id": user_id})
    except Exception:  # noqa: BLE001
        pass
