"""Rotate and upload application logs to S3.

Run on the batch box with the deploy user:

    AWS_ACCESS_KEY_ID={{FAKE_AWS_KEY_ID}} python rotate_logs.py

The bucket is acme-prod-logs in us-east-1.
"""
import gzip
import pathlib
import shutil

LOG_DIR = pathlib.Path("/var/log/acme")


def rotate() -> list[pathlib.Path]:
    out = []
    for p in LOG_DIR.glob("*.log"):
        gz = p.with_suffix(".log.gz")
        with p.open("rb") as src, gzip.open(gz, "wb") as dst:
            shutil.copyfileobj(src, dst)
        out.append(gz)
    return out


if __name__ == "__main__":
    print(rotate())
