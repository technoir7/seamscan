"""Rebuild the bundled snapshot of the most-used npm and PyPI names (ADR-004).

    uv run python scripts/build_snapshot.py

Writes src/seamscan/supply/data/{npm,pypi}.txt (sorted, one name per line) and the README
next to them that records where the names came from. The sources are pinned to a tag, so
a rebuild is reproducible; bump the tags below to refresh.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from seamscan.facts.dependencies import pypi_name

LIMIT = 10_000
DATA = Path(__file__).resolve().parent.parent / "src" / "seamscan" / "supply" / "data"

PYPI_TAG = "2026.10.1"
PYPI_URL = (
    f"https://raw.githubusercontent.com/hugovk/top-pypi-packages/{PYPI_TAG}/"
    "top-pypi-packages.min.json"
)
NPM_TAG = "1.13.0"
NPM_URL = f"https://raw.githubusercontent.com/wooorm/npm-high-impact/{NPM_TAG}/lib/top.js"

# Names as the registries allow them; anything else in a source file is skipped, so a
# malformed download can't put arbitrary text into the package.
_NPM_NAME = re.compile(r"^(?:@[a-z0-9][a-z0-9._~-]*/)?[a-zA-Z0-9][a-zA-Z0-9._~-]*$")
_PYPI_NAME = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")

README = """\
# Bundled registry snapshot

The most-used package names, so that well-known dependencies need no registry request
and `--offline` can still vouch for them (ADR-004, spec §7.7). A name here counts as
existing, long established and widely used. One name per line, sorted.

Rebuild with `uv run python scripts/build_snapshot.py`. Built {built}.

## `npm.txt`: {npm_count} names

- Source: the first {limit} of `top` in
  [wooorm/npm-high-impact](https://github.com/wooorm/npm-high-impact) {npm_tag}
  ({npm_url}). These are the packages npm calls high-impact (at least 1M weekly downloads
  or 500 dependents), most downloaded first. The source notes that download counts can be
  gamed, so a few names may be less established than their rank suggests.
- License: MIT, © Titus Wormer.

## `pypi.txt`: {pypi_count} names

- Source: the first {limit} of
  [hugovk/top-pypi-packages](https://github.com/hugovk/top-pypi-packages) release
  {pypi_tag} ({pypi_url}): the most-downloaded projects over 30 days, from the public
  ClickHouse PyPI dataset. Names are PEP 503-normalized.
- License: CC-BY-4.0 (the Zenodo record of the release), © Hugo van Kemenade.
"""


def _get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "seamscan build_snapshot"})
    with urllib.request.urlopen(request, timeout=60) as reply:
        return reply.read()


def _first(names: list[str], pattern: re.Pattern[str], what: str) -> list[str]:
    kept: list[str] = []
    seen: set[str] = set()
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        if not pattern.match(name):
            print(f"skipping odd {what} name {name!r}", file=sys.stderr)
            continue
        kept.append(name)
        if len(kept) == LIMIT:
            break
    if len(kept) < LIMIT:
        sys.exit(f"{what}: only {len(kept)} names; the source format may have changed")
    return kept


def npm_names() -> list[str]:
    text = _get(NPM_URL).decode("utf-8")
    if "export const top = [" not in text:
        sys.exit("npm: lib/top.js no longer exports `top`; check the source")
    return _first(re.findall(r"^\s*'([^']+)',?$", text, re.MULTILINE), _NPM_NAME, "npm")


def pypi_names() -> list[str]:
    doc = json.loads(_get(PYPI_URL))
    rows = sorted(doc["rows"], key=lambda r: -int(r["download_count"]))
    return _first([pypi_name(str(r["project"])) for r in rows], _PYPI_NAME, "PyPI")


def main() -> None:
    npm, pypi = npm_names(), pypi_names()
    for name, names in (("npm", npm), ("pypi", pypi)):
        (DATA / f"{name}.txt").write_text("".join(f"{n}\n" for n in sorted(names)))
    (DATA / "README.md").write_text(
        README.format(
            built=datetime.now(UTC).date().isoformat(),
            limit=f"{LIMIT:,}",
            npm_count=f"{len(npm):,}",
            npm_tag=NPM_TAG,
            npm_url=NPM_URL,
            pypi_count=f"{len(pypi):,}",
            pypi_tag=PYPI_TAG,
            pypi_url=PYPI_URL,
        )
    )
    print(f"wrote {len(npm)} npm and {len(pypi)} PyPI names to {DATA}")


if __name__ == "__main__":
    main()
