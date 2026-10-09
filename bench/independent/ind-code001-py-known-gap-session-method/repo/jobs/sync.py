import requests

s = requests.Session()
s.headers["Authorization"] = "Bearer abc"


def pull(url: str):
    return s.get(url, verify=False, timeout=20).json()
