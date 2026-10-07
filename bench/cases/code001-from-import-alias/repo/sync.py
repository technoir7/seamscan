from requests import post


def push(url, payload):
    return post(url, json=payload, verify=False)
