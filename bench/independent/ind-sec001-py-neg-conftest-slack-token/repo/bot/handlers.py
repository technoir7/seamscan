import os


def token() -> str:
    return os.environ["SLACK_BOT_TOKEN"]
