import requests

CA = "/etc/ssl/corp-ca.pem"


def public_get(url: str):
    return requests.get(url, timeout=10)


def internal_get(url: str):
    return requests.get(url, verify=CA, timeout=10)


def pinned(url: str):
    return requests.get(url, verify="/etc/ssl/ca.pem", timeout=10)
