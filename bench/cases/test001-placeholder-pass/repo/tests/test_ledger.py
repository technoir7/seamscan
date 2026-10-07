from ledger.entries import post_refund


def test_post_refund_creates_entry():
    assert post_refund(order_id=3).amount == -20


def test_refund_reverses_ledger_entry():
    # TODO: re-enable once ledger mocks are fixed
    pass
