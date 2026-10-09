def is_demo(token: str) -> bool:
    return token in ("demo-token", "qa-token")


def handle(token: str):
    if is_demo(token):
        return {"mode": "sandbox"}
    return {"mode": "live"}
