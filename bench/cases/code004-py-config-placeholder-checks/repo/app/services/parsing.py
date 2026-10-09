import os

from app.settings import settings


def llama_enabled() -> bool:
    return bool(settings.LLAMA_API_KEY and settings.LLAMA_API_KEY != "llx-placeholder")


def stripe_configured() -> bool:
    key = os.getenv("STRIPE_SECRET_KEY")
    return not (not key or key == "sk_test_replace_me")


def admin_token_is_default() -> bool:
    return os.environ.get("ADMIN_TOKEN") == "change-this-token"
