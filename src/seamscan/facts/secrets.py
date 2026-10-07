"""Recognize credential-shaped strings and redact them (spec §6.4, §7.1). Pure."""

from __future__ import annotations

import base64
import binascii
import json
import re
from dataclasses import dataclass
from typing import Literal

Kind = Literal["secret", "publishable", "test"]


@dataclass(frozen=True)
class SecretMatch:
    provider: str
    kind: Kind
    value: str
    start: int = 0
    end: int = 0


# Order matters: more specific prefixes come before more general ones (sk-ant- before sk-).
_PATTERNS: tuple[tuple[str, Kind, re.Pattern[str]], ...] = (
    ("Stripe", "secret", re.compile(r"\b(?:sk|rk)_live_[0-9A-Za-z]{16,}")),
    ("Stripe", "test", re.compile(r"\b(?:sk|rk)_test_[0-9A-Za-z]{16,}")),
    ("Stripe", "publishable", re.compile(r"\bpk_(?:live|test)_[0-9A-Za-z]{16,}")),
    ("Anthropic", "secret", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    ("OpenAI", "secret", re.compile(r"\bsk-proj-[A-Za-z0-9_-]{20,}")),
    ("OpenAI", "secret", re.compile(r"\bsk-[A-Za-z0-9]{40,}")),
    ("GitHub", "secret", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}")),
    ("GitHub", "secret", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}")),
    ("AWS", "secret", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("Supabase", "secret", re.compile(r"\bsb_secret_[A-Za-z0-9_-]{16,}")),
    ("Supabase", "publishable", re.compile(r"\bsb_publishable_[A-Za-z0-9_-]{16,}")),
    ("Slack", "secret", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}")),
)

_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")


def _jwt_role(token: str) -> str | None:
    """Read the `role` claim without verifying the signature: classification only."""
    try:
        payload = token.split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except (IndexError, ValueError, binascii.Error):
        return None
    if not isinstance(claims, dict):
        return None
    role = claims.get("role")  # type: ignore[union-attr]
    return role if isinstance(role, str) else None


def _jwt_match(token: str, start: int, end: int) -> SecretMatch | None:
    role = _jwt_role(token)
    if role == "service_role":
        return SecretMatch("Supabase service_role JWT", "secret", token, start, end)
    if role == "anon":
        return SecretMatch("Supabase anon JWT", "publishable", token, start, end)
    return None


def find_secrets(text: str) -> list[SecretMatch]:
    """Every credential-shaped substring, in order, without overlaps."""
    found: list[SecretMatch] = []
    taken: list[tuple[int, int]] = []

    def free(s: int, e: int) -> bool:
        return all(e <= a or s >= b for a, b in taken)

    for provider, kind, pattern in _PATTERNS:
        for m in pattern.finditer(text):
            if free(m.start(), m.end()):
                found.append(SecretMatch(provider, kind, m.group(0), m.start(), m.end()))
                taken.append((m.start(), m.end()))
    for m in _JWT.finditer(text):
        jm = _jwt_match(m.group(0), m.start(), m.end())
        if jm and free(m.start(), m.end()):
            found.append(jm)
            taken.append((m.start(), m.end()))
    return sorted(found, key=lambda s: s.start)


def classify(value: str) -> SecretMatch | None:
    """Classify a whole value (e.g. a string literal or an .env value)."""
    for m in find_secrets(value):
        if m.start == 0 and m.end == len(value):
            return m
    return None


_PREFIX = re.compile(r"^(?:[A-Za-z]{2,4}[_-](?:[a-z]{3,9}[_-])?|AKIA|ASIA|eyJ)")


def redact(value: str) -> str:
    """Keep the provider prefix and a few characters at each end: sk_live_51Hx…L2mN4."""
    prefix = m.group(0) if (m := _PREFIX.match(value)) else ""
    rest = value[len(prefix) :]
    if len(rest) <= 12:
        return prefix + "…"
    return f"{prefix}{rest[:4]}…{rest[-5:]}"
