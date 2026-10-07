from payments.gateway import CardDeclined, charge


def test_declined_card_raises():
    try:
        charge(card="declined-test-card", amount=500)
    except CardDeclined:
        return
    assert False, "charge should have raised CardDeclined"
