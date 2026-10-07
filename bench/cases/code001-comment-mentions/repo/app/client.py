import requests


def fetch(url):
    # never pass verify=False here, the proxy re-signs certs
    return requests.get(url, timeout=10)
