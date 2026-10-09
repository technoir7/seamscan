from feed.parser import parse_quote


def test_quote_price_is_a_number():
    quote = parse_quote('{"sym": "ACME", "px": "12.5"}')
    assert quote.price == quote.price  # NaN != NaN, so this fails for NaN
    assert quote.price > 0
