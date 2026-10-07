import stripe


class StripeGateway:
    def __init__(self, api_key: str) -> None:
        self.client = stripe.StripeClient(api_key)

    def charge(self, customer_id: str, amount_cents: int):
        return self.client.payment_intents.create(
            params={"customer": customer_id, "amount": amount_cents, "currency": "usd"}
        )

    def refund(self, payment_intent_id: str):
        raise NotImplementedError()
