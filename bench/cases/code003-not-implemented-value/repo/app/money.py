class Money:
    def __init__(self, cents: int, currency: str) -> None:
        self.cents = cents
        self.currency = currency

    def __eq__(self, other):
        if not isinstance(other, Money):
            return NotImplemented
        return (self.cents, self.currency) == (other.cents, other.currency)


def render_report(report, fmt: str) -> bytes:
    try:
        return report.render(fmt)
    except NotImplementedError:
        return report.render("csv")
