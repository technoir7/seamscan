import stripe
import pytest


@pytest.fixture(autouse=True)
def fake_key(monkeypatch):
    stripe.api_key = "{{FAKE_STRIPE_LIVE}}"


def test_key_is_set():
    assert stripe.api_key
