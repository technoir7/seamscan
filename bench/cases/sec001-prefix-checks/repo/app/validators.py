"""Sanity checks on credentials before the app starts."""

from app.settings import settings


def check_stripe_mode() -> None:
    key = settings.stripe_secret_key
    if not key.startswith(("sk_", "rk_")):
        raise ValueError("STRIPE_SECRET_KEY must be a secret or restricted key")
    if settings.environment == "production" and key.startswith("sk_test_"):
        raise ValueError("refusing to run production with a Stripe test key")


def looks_like_github_token(value: str) -> bool:
    return value.startswith(("ghp_", "github_pat_", "gho_"))
