import os

import stripe

stripe.api_key = os.environ["STRIPE_SECRET_KEY"]


def create_checkout_session(price_id: str):
    return stripe.checkout.Session.create(
        mode="subscription", line_items=[{"price": price_id, "quantity": 1}]
    )
