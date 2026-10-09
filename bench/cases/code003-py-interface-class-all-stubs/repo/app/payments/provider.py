class PaymentProvider:
    """Interface for payment back ends. See stripe_provider.py and paddle_provider.py."""

    def create_checkout(self, user, plan):
        raise NotImplementedError

    def verify_webhook(self, payload, signature):
        return True

    def cancel(self, subscription_id):
        pass
