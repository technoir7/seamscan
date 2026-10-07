from abc import ABC


class PaymentProvider(ABC):
    def charge(self, customer_id: str, amount_cents: int) -> str:
        raise NotImplementedError("subclasses implement charge()")

    def refund(self, charge_id: str) -> None:
        raise NotImplementedError("subclasses implement refund()")
