class PaymentProvider:
    def charge(self, amount: int, token: str) -> str:
        raise NotImplementedError("charge")

    def refund(self, payment_id: str) -> None:
        raise NotImplementedError()


class StripeProvider(PaymentProvider):
    def charge(self, amount: int, token: str) -> str:
        return f"ch_{token}_{amount}"
