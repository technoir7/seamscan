import base64
import json

from bench.fake_secrets import FAKES
from seamscan.facts.roles import PackageKind, Role, role_of
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


def test_supabase_cli_demo_keys_are_demo_values_whatever_their_role():
    for role in ("service_role", "anon"):
        m = classify(jwt({"iss": "supabase-demo", "role": role}))
        assert m is not None and m.kind == "demo", role
    assert classify(jwt({"iss": "supabase-demo", "role": "authenticated"})) is None


def test_find_secrets_in_text():
    text = f'key = "{FAKES["FAKE_STRIPE_LIVE"]}"  # and {FAKES["FAKE_STRIPE_PK_LIVE"]}'
    kinds = [m.kind for m in find_secrets(text)]
    assert kinds == ["secret", "publishable"]


def test_redaction_never_returns_the_value():
    for value in FAKES.values():
        r = redact(value)
        assert value not in r and "…" in r
    assert redact(FAKES["FAKE_STRIPE_LIVE"]).startswith("sk_live_51Hx")


def test_short_values_reveal_little():
    r = redact(FAKES["FAKE_AWS_KEY_ID"])  # AKIA + 16 characters
    shown = r.removeprefix("AKIA").replace("…", "")
    assert len(shown) <= 4


def test_js_roles():
    assert role_of("components/Button.test.tsx") is Role.TEST
    assert role_of("src/__tests__/api.ts") is Role.TEST
    assert role_of("e2e/login.spec.ts") is Role.TEST
    assert role_of("app/components/Chat.tsx", "use client") is Role.CLIENT
    assert role_of("server.js", kind=PackageKind.BACKEND) is Role.SERVER
    assert role_of("app/actions.ts", "use server") is Role.SERVER
    assert role_of("app/api/messages/route.ts") is Role.SERVER
    assert role_of("middleware.ts") is Role.SERVER
    assert role_of("pages/api/checkout.ts") is Role.SERVER
    assert role_of("app/dashboard/page.tsx") is Role.SERVER  # server component by default
    assert role_of("supabase/functions/notify/index.ts") is Role.SERVER
    assert role_of("src/lib/db.server.ts") is Role.SERVER
    assert role_of("src/App.tsx") is Role.CLIENT  # Vite / CRA
    assert role_of("src/server/routes.ts") is Role.SERVER
    assert role_of("server.js") is Role.UNKNOWN
