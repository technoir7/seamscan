import os

os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ["SESSION_SECRET"] = os.environ.get("SESSION_SECRET", "unit-test-session")


def test_env():
    assert os.environ["JWT_SECRET"]
