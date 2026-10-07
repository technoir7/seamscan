from app import webhooks


def fake_verify_signature(payload, signature):
    return True


class FakeGateway:
    def refund(self, payment_intent_id):
        raise NotImplementedError


def test_webhook_accepts_event(monkeypatch, client):
    monkeypatch.setattr(webhooks, "verify_signature", fake_verify_signature)
    resp = client.post("/webhooks/stripe", data=b"{}", headers={"Stripe-Signature": "t=1"})
    assert resp.status_code == 200
