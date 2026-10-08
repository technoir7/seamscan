"""The explicit list of rules that run. No discovery magic (spec §5.2)."""

from __future__ import annotations

from seamscan.rules import (
    code,
    deserialize,
    firebase,
    injection,
    secrets,
    supabase,
    tests_integrity,
    web,
)
from seamscan.rules.base import Rule

RULES: tuple[Rule, ...] = (
    *secrets.RULES,
    *code.RULES,
    *injection.RULES,
    *deserialize.RULES,
    *tests_integrity.RULES,
    *web.RULES,
    *supabase.RULES,
    *firebase.RULES,
)
