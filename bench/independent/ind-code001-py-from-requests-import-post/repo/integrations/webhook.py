from requests import post


def notify(payload: dict) -> None:
    post("https://hooks.internal.example/alert", json=payload, verify=False, timeout=5)
