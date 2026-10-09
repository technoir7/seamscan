"""One HTTP GET, the only network call seamscan makes (spec §7.7). stdlib `urllib`.

The lookup takes the fetch function as a parameter, so tests pass a fake and nothing
else in seamscan opens a socket.
"""

from __future__ import annotations

import gzip
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from seamscan import __version__

TIMEOUT_SECONDS = 10
USER_AGENT = f"seamscan/{__version__} (+https://github.com/technoir7/seamscan)"


@dataclass(frozen=True)
class Response:
    status: int
    body: bytes = b""
    retry_after: str | None = None  # the Retry-After header, for 429


class FetchError(Exception):
    """No HTTP answer at all (timeout, DNS, refused, broken connection). The message is a
    short reason fit for a finding."""


Fetch = Callable[[str, Mapping[str, str]], Response]


def fetch_url(url: str, headers: Mapping[str, str], timeout: float = TIMEOUT_SECONDS) -> Response:
    """GET `url`. Any HTTP status is a Response; only a transport failure raises FetchError."""
    # Imported here: http.client costs ~5 ms at startup, and most runs (the PostToolUse
    # hook, --offline, a warm cache) never make a request.
    import http.client
    import urllib.error
    import urllib.request

    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip", **headers}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as reply:
            body = _body(reply.read(), reply.headers.get("Content-Encoding"))
            return Response(reply.status, body)
    except urllib.error.HTTPError as exc:
        with exc:
            body = _body(exc.read(), exc.headers.get("Content-Encoding"))
            return Response(exc.code, body, exc.headers.get("Retry-After"))
    except TimeoutError as exc:
        raise FetchError("timed out") from exc
    except urllib.error.URLError as exc:
        reason = exc.reason
        if isinstance(reason, TimeoutError):
            raise FetchError("timed out") from exc
        raise FetchError(f"network error: {reason}") from exc
    except (OSError, http.client.HTTPException, EOFError) as exc:
        raise FetchError(f"network error: {type(exc).__name__}: {exc}") from exc


def _body(raw: bytes, encoding: str | None) -> bytes:
    # Packuments are JSON and compress about 10:1; asking for gzip saves most of the bytes.
    if (encoding or "").lower() == "gzip":
        try:
            return gzip.decompress(raw)
        except (OSError, EOFError):
            return b""  # an undecodable body reads as malformed JSON downstream
    return raw
