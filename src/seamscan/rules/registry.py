"""The explicit list of rules that run. No discovery magic (spec §5.2)."""

from __future__ import annotations

from seamscan.rules import code
from seamscan.rules.base import Rule

RULES: tuple[Rule, ...] = (*code.RULES,)
