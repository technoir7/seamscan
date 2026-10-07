"""SC-WEB rules: server routes and web configuration (spec §7.4).

Each rule has its own module, since they change for unrelated reasons (auth conventions,
HTTP client APIs, framework config); this one only lists them for the registry.
"""

from __future__ import annotations

from seamscan.rules import web_auth, web_config, web_ssrf
from seamscan.rules.base import Rule

RULES: tuple[Rule, ...] = (*web_auth.RULES, *web_ssrf.RULES, *web_config.RULES)
