from app.rules import evaluate


def run_case(rule, facts, expected):
    got = evaluate(rule, facts)
    assert got == expected, f"{rule}: {got!r} != {expected!r}"
