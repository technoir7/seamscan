"""The explicit list of rules that run. No discovery magic (spec §5.2)."""

from __future__ import annotations

from seamscan.model import RuleMeta
from seamscan.rules import (
    code,
    dependencies,
    deserialize,
    firebase,
    injection,
    meta,
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
    *dependencies.RULES,
)

# Every rule id a finding can carry, for outputs that describe rules (SARIF, the report).
ALL_META: tuple[RuleMeta, ...] = (*(r.meta for r in RULES), *meta.META)
