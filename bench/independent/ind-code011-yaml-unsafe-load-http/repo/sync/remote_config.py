import requests
import yaml


def fetch_config(url: str) -> dict:
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return yaml.unsafe_load(resp.text)
