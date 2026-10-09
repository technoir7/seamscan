# Bundled registry snapshot

The most-used package names, so that well-known dependencies need no registry request
and `--offline` can still vouch for them (ADR-004, spec §7.7). A name here counts as
existing, long established and widely used. One name per line, sorted.

Rebuild with `uv run python scripts/build_snapshot.py`. Built 2026-10-09.

## `npm.txt`: 10,000 names

- Source: the first 10,000 of `top` in
  [wooorm/npm-high-impact](https://github.com/wooorm/npm-high-impact) 1.13.0
  (https://raw.githubusercontent.com/wooorm/npm-high-impact/1.13.0/lib/top.js). These are the packages npm calls high-impact (at least 1M weekly downloads
  or 500 dependents), most downloaded first. The source notes that download counts can be
  gamed, so a few names may be less established than their rank suggests.
- License: MIT, © Titus Wormer.

## `pypi.txt`: 10,000 names

- Source: the first 10,000 of
  [hugovk/top-pypi-packages](https://github.com/hugovk/top-pypi-packages) release
  2026.10.1 (https://raw.githubusercontent.com/hugovk/top-pypi-packages/2026.10.1/top-pypi-packages.min.json): the most-downloaded projects over 30 days, from the public
  ClickHouse PyPI dataset. Names are PEP 503-normalized.
- License: CC-BY-4.0 (the Zenodo record of the release), © Hugo van Kemenade.
