import logging
from fastapi import HTTPException

from api.db import db

log = logging.getLogger(__name__)


def save_item(item):
    try:
        db.session.add(item)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        log.exception("save failed")
        raise HTTPException(500, "could not save") from exc


def lookup(key):
    try:
        return db.cache.fetch(key)
    except Exception:
        logging.getLogger("x").warning("fetch failed", exc_info=True)
        return None
