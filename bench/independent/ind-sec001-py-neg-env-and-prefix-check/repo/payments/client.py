import os
import stripe


def configure() -> None:
    key = os.environ["STRIPE_SECRET_KEY"]
    if key.startswith("sk_test_") and os.environ.get("APP_ENV") == "production":
        raise RuntimeError("test key configured in production")
    stripe.api_key = key
