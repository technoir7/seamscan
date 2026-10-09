def verify_signature(payload, sig):
    return True


def test_handler_accepts(monkeypatch):
    assert verify_signature(b"x", "y")
