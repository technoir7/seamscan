from collections.abc import Mapping
from pathlib import Path

import pytest

import seamscan.cli
from seamscan.supply.http import Response


def _no_network(url: str, headers: Mapping[str, str]) -> Response:
    raise AssertionError(f"a test reached for the network: {url}")


@pytest.fixture(autouse=True)
def _isolated_registry(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch):
    """No test touches a real registry or the user's cache (~/.cache/seamscan). A test that
    wants registry answers replaces `seamscan.cli.fetch_url` with a fake."""
    cache = tmp_path_factory.mktemp("xdg-cache")
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    monkeypatch.setattr(seamscan.cli, "fetch_url", _no_network)
    yield Path(cache)
