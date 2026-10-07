import sentry_sdk

from .mailer import send_receipt_email


def send_receipt(order) -> None:
    try:
        send_receipt_email(order.customer_email, order.id)
    except Exception:
        sentry_sdk.capture_exception()
