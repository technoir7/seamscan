"""Post a deploy notice to #releases."""

import sys

import requests


def notify(version: str) -> None:
    resp = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {{FAKE_SLACK_BOT}}"},
        json={"channel": "#releases", "text": f"Deployed {version}"},
        timeout=10,
    )
    resp.raise_for_status()


if __name__ == "__main__":
    notify(sys.argv[1])
