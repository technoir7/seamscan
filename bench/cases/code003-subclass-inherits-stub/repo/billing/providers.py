import stripe


class PaymentProvider:
    def charge(self, customer_id: str, amount_cents: int) -> str:
        raise NotImplementedError

    def refund(self, charge_id: str) -> None:
        raise NotImplementedError("refunds are not wired up yet")


class StripeProvider(PaymentProvider):
    def charge(self, customer_id: str, amount_cents: int) -> str:
        intent = stripe.PaymentIntent.create(
            customer=customer_id, amount=amount_cents, currency="usd", confirm=True
        )
        return intent.id


provider = StripeProvider()
