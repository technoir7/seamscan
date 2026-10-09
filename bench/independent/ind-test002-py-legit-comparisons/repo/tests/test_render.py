import pytest

from site.render import render, parse_user


def test_health(client):
    response = client.get("/health")
    assert (response.status_code == 200), "health check failed"
    assert response.status_code == 200, "health check failed"


def test_render_is_deterministic():
    data = {"title": "Hello", "items": [1, 2, 3]}
    assert render(data) == render(data)


def test_email_lowercased():
    user = parse_user("Ada@Example.com")
    assert user.email == user.email.lower()


def test_user_tuple():
    user = parse_user("ada@example.com")
    assert (user.email, user.active) == ("ada@example.com", True)


def test_raises():
    with pytest.raises(ValueError):
        parse_user("")
        assert False, "should have raised"
