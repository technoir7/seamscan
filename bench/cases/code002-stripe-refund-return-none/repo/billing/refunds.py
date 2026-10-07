import stripe


def refund_order(order):
    try:
        refund = stripe.Refund.create(payment_intent=order.payment_intent_id)
        order.refund_id = refund.id
        order.save()
        return refund
    except Exception:
        return None
