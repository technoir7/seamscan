import base64
import json

from bench.fake_secrets import FAKES
from seamscan.facts.roles import Role, role_of
from seamscan.facts.secrets import classify, find_secrets, redact


def jwt(payload: dict[str, str]) -> str:
    def b64(d: dict[str, str]) -> str:
        return base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")

    return f"{b64({'alg': 'HS256', 'typ': 'JWT'})}.{b64(payload)}.c2lnbmF0dXJlLXZhbHVl"


def test_roles():
    assert role_of("tests/test_api.py") is Role.TEST
    assert role_of("app/test_utils.py") is Role.TEST
    assert role_of("pkg/foo_test.py") is Role.TEST
    assert role_of("conftest.py") is Role.TEST
    assert role_of("app/views.py") is Role.SERVER
    assert role_of("README.md") is Role.UNKNOWN


def test_classifies_provider_secrets():
    assert classify(FAKES["FAKE_STRIPE_LIVE"]).kind == "secret"
    assert classify(FAKES["FAKE_OPENAI_PROJ"]).provider == "OpenAI"
    assert classify(FAKES["FAKE_GITHUB_PAT"]).kind == "secret"
    assert classify(FAKES["FAKE_AWS_KEY_ID"]).provider == "AWS"


def test_publishable_and_test_keys_are_not_secrets():
    assert classify(FAKES["FAKE_STRIPE_PK_LIVE"]).kind == "publishable"
    assert classify(FAKES["FAKE_STRIPE_TEST"]).kind == "test"


def test_supabase_jwt_role_decides():
    assert classify(jwt({"role": "service_role", "iss": "supabase"})).kind == "secret"
    assert classify(jwt({"role": "anon", "iss": "supabase"})).kind == "publishable"
    assert classify(jwt({"sub": "123"})) is None


def test_find_secrets_in_text():
    text = f'key = "{FAKES["FAKE_STRIPE_LIVE"]}"  # and {FAKES["FAKE_STRIPE_PK_LIVE"]}'
    kinds = [m.kind for m in find_secrets(text)]
    assert kinds == ["secret", "publishable"]


def test_redaction_never_returns_the_value():
    for value in FAKES.values():
        r = redact(value)
        assert value not in r and "…" in r
    assert redact(FAKES["FAKE_STRIPE_LIVE"]).startswith("sk_live_51Hx")
