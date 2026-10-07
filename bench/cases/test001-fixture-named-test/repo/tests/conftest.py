import pytest

from accounts.models import User


@pytest.fixture
def test_user():
    return User(id=1, email="ada@example.com")


@pytest.fixture
def test_client(test_user):
    from api.app import create_app

    app = create_app()
    app.login_as(test_user)
    return app.test_client()
