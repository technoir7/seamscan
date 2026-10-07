OPERATORS = ("and", "or", "not")


def tokenize(rule: str) -> list[str]:
    return rule.replace("(", " ( ").replace(")", " ) ").split()


def to_postfix(rule: str) -> list[str]:
    """Shunting-yard for feature-flag rules like `beta and (staff or not eu)`."""
    output: list[str] = []
    stack: list[str] = []
    for token in tokenize(rule):
        if token == "(":
            stack.append(token)
        elif token == ")":
            while stack and stack[-1] != "(":
                output.append(stack.pop())
            stack.pop()
        elif token in ("and", "or", "not"):
            while stack and stack[-1] in OPERATORS and token != "not":
                output.append(stack.pop())
            stack.append(token)
        else:
            output.append(token)
    while stack:
        output.append(stack.pop())
    return output
