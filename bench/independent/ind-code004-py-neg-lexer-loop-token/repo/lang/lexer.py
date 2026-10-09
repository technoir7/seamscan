KEYWORDS = {"and", "or", "not"}


def count_ops(tokens: list[str]) -> int:
    n = 0
    for token in tokens:
        if token == "and" or token == "or":
            n += 1
    return n
