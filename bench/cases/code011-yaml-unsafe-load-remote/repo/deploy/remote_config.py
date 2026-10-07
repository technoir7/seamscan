import requests
import yaml

CONFIG_URL = "https://config.internal.acme.dev/service.yaml"


def fetch_config(url: str = CONFIG_URL) -> dict:
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return yaml.unsafe_load(resp.text)
