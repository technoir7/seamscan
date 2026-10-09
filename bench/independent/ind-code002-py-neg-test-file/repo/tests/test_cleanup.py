import pytest

from app.db import db


@pytest.fixture
def clean():
    yield
    try:
        db.session.rollback()
        db.session.commit()
    except Exception:
        pass


def test_noop(clean):
    assert True
