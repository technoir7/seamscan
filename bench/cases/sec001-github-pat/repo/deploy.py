import requests

TOKEN = "{{FAKE_GITHUB_PAT}}"


def release(tag):
    return requests.post("https://api.github.com/repos/o/r/releases", headers={"Authorization": f"token {TOKEN}"}, json={"tag_name": tag}, timeout=10)
