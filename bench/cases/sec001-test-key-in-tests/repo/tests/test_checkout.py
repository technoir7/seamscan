import stripe

from app.billing import create_checkout_session


def test_checkout_session_uses_test_mode(monkeypatch):
    monkeypatch.setattr(stripe, "api_key", "{{FAKE_STRIPE_TEST}}")
    created = {}
    monkeypatch.setattr(stripe.checkout.Session, "create", lambda **kw: created.update(kw) or kw)
    create_checkout_session("price_123")
    assert created["mode"] == "subscription"
