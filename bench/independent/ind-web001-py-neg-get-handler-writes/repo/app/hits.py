from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .database import get_db
from .models import Page

router = APIRouter()


@router.get("/pages/{slug}")
def read_page(slug: str, db: Session = Depends(get_db)):
    page = db.query(Page).filter_by(slug=slug).one()
    page.hits += 1
    db.commit()
    return {"title": page.title, "hits": page.hits}
