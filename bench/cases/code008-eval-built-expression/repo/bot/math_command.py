def handle_math(a: str, op: str, b: str) -> str:
    if op not in {"+", "-", "*", "/"}:
        return "unsupported operator"
    return str(eval(f"{a} {op} {b}"))
