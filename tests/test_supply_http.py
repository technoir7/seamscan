"""The real HTTP GET, against a local server: statuses are answers, transport failures raise."""

from __future__ import annotations

import gzip
import socket
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from seamscan import __version__
from seamscan.supply.http import FetchError, fetch_url

seen: dict[str, str] = {}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - the stdlib's name
        seen.update({k: v for k, v in self.headers.items()})
        if self.path == "/gzip":
            body = gzip.compress(b'{"ok": true}')
            self.send_response(200)
            self.send_header("Content-Encoding", "gzip")
        elif self.path == "/limited":
            body = b"slow down"
            self.send_response(429)
            self.send_header("Retry-After", "3")
        elif self.path == "/slow":
            threading.Event().wait(1.0)
            body = b"late"
            self.send_response(200)
        else:
            body = b'{"error":"Not found"}'
            self.send_response(404)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture(scope="module")
def server() -> Iterator[str]:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def test_names_seamscan_and_decodes_gzip(server: str):
    reply = fetch_url(f"{server}/gzip", {"Accept": "application/json"})
    assert (reply.status, reply.body) == (200, b'{"ok": true}')
    assert seen["User-Agent"].startswith(f"seamscan/{__version__}")
    assert seen["Accept"] == "application/json"


def test_http_errors_are_responses(server: str):
    assert fetch_url(f"{server}/nope", {}).status == 404
    limited = fetch_url(f"{server}/limited", {})
    assert (limited.status, limited.retry_after) == (429, "3")


def test_timeout_raises_fetch_error(server: str):
    with pytest.raises(FetchError, match="timed out"):
        fetch_url(f"{server}/slow", {}, timeout=0.2)


def test_refused_connection_raises_fetch_error():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]  # closed again before the request: nothing listens
    with pytest.raises(FetchError, match="network error"):
        fetch_url(f"http://127.0.0.1:{port}/", {})
