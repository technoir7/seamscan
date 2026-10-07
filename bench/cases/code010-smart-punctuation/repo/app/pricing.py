# “Café” pricing — prices are in cents; see the spec §4.
prix_café = 350


def price_label(cents: int) -> str:
    return f"€{cents / 100:.2f} – incl. VAT"
