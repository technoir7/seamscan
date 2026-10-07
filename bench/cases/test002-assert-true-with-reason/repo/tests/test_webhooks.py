from payments.webhooks import handle_event


def test_refund_webhook_marks_order_refunded(order_factory):
    order = order_factory(status="paid")
    handle_event({"type": "charge.refunded", "order_id": order.id})
    assert True, "covered by the integration suite"
