import requests

CA = "/etc/ssl/internal-ca.pem"


def fetch(url):
    return requests.get(url, verify=CA, timeout=10)
