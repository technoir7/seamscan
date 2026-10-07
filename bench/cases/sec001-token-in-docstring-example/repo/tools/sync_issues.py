"""Sync GitHub issues into the local tracker.

Usage:
    python tools/sync_issues.py acme/web

Quick manual check of the API:
    curl -H "Authorization: token {{FAKE_GITHUB_PAT}}" https://api.github.com/repos/acme/web/issues
"""

import os
import sys

import requests

TOKEN = os.environ["GITHUB_TOKEN"]


def fetch_issues(repo: str) -> list[dict]:
    resp = requests.get(
        f"https://api.github.com/repos/{repo}/issues",
        headers={"Authorization": f"token {TOKEN}"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    print(len(fetch_issues(sys.argv[1])))
