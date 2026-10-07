"""SC-CODE rules: risky code patterns in Python and TS/JS (spec §7.5)."""

from __future__ import annotations

import ast
from collections.abc import Iterator

from seamscan.model import Confidence, Finding, Severity
from seamscan.parse.python import is_constant, keyword, location, qualified_name, snippet
from seamscan.rules.base import Rule, RuleContext, finding, meta

TLS_DISABLED = meta(
    "SC-CODE-001",
    "TLS verification disabled",
    Severity.HIGH,
    Confidence.HIGH,
    ("CWE-295",),
    frozenset({"python"}),
    "Certificate checks are turned off, so anyone on the network path can impersonate the server.",
)

_HTTP_CLIENT_PREFIXES = ("requests.", "httpx.")


def _tls_disabled(ctx: RuleContext) -> Iterator[Finding]:
    for module in ctx.python:
        for node in ast.walk(module.tree):
            if isinstance(node, ast.Call):
                name = qualified_name(module, node.func) or ""
                if name.startswith(_HTTP_CLIENT_PREFIXES) and is_constant(
                    keyword(node, "verify"), False
                ):
                    yield finding(
                        TLS_DISABLED,
                        location(module, node),
                        f"`{name}` called with verify=False",
                        snippet(module, node),
                    )
                elif name.startswith("aiohttp.") and is_constant(keyword(node, "ssl"), False):
                    yield finding(
                        TLS_DISABLED,
                        location(module, node),
                        f"`{name}` called with ssl=False",
                        snippet(module, node),
                    )
                elif name == "ssl._create_unverified_context":
                    yield finding(
                        TLS_DISABLED,
                        location(module, node),
                        "unverified SSL context created",
                        snippet(module, node),
                    )
            elif (
                isinstance(node, ast.Attribute) and qualified_name(module, node) == "ssl.CERT_NONE"
            ):
                yield finding(
                    TLS_DISABLED,
                    location(module, node),
                    "certificate verification mode set to ssl.CERT_NONE",
                    snippet(module, node),
                )


RULES: tuple[Rule, ...] = (Rule(TLS_DISABLED, _tls_disabled),)
