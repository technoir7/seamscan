"""SC-DEP: dependencies the registry can't vouch for (spec §7.7, ADR-004).

The rules only read `ctx.registry`, plain data gathered at the I/O edge. Without it they
report nothing, and a dependency the edge didn't look up (allow-listed, privately mapped,
not in this change) has no facts and is never reported.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta

from seamscan.facts.dependencies import Dependency, added_in_change
from seamscan.model import (
    Confidence,
    Ecosystem,
    Finding,
    PackageFacts,
    RegistryView,
    Severity,
)
from seamscan.rules.base import Rule, RuleContext, finding, meta
from seamscan.rules.meta import DEPENDENCY_UNVERIFIED

MISSING = meta(
    "SC-DEP-001",
    "Dependency that doesn't exist",
    Severity.HIGH,
    Confidence.HIGH,
    ("CWE-1357",),
    frozenset({"python", "javascript"}),
    "The registry has no package with this name: AI tools invent package names, and "
    "attackers register them.",
)

TOO_NEW = meta(
    "SC-DEP-002",
    "Dependency too new or obscure to trust",
    Severity.MEDIUM,
    Confidence.MEDIUM,
    (),
    frozenset({"python", "javascript"}),
    "The package was published days ago or barely anyone installs it: check it is the one "
    "you meant before trusting it.",
)

INSTALL_SCRIPTS = meta(
    "SC-DEP-003",
    "New dependency runs code at install",
    Severity.MEDIUM,
    Confidence.HIGH,
    ("CWE-829",),
    frozenset({"javascript"}),
    "This change adds a package that runs its own scripts when it is installed.",
)

_REGISTRY = {Ecosystem.NPM: "npm", Ecosystem.PYPI: "PyPI"}
# `prepare` and the rest don't run when a package is installed from the registry.
_INSTALL_HOOKS = ("preinstall", "install", "postinstall")


def _looked_up(ctx: RuleContext) -> Iterator[tuple[Dependency, PackageFacts, RegistryView]]:
    view = ctx.registry
    if view is None:
        return
    for d in ctx.project.dependencies:
        facts = view.packages.get(d.ref)
        if facts is not None:
            yield d, facts, view


def _evidence(ctx: RuleContext, d: Dependency) -> str:
    # Scan mode: an unchanged manifest arrives only as context; its finding is out of
    # scope anyway, so the name is evidence enough.
    for f in ctx.files:
        if f.path == d.location.path:
            lines = f.text.splitlines()
            return lines[d.location.start_line - 1].strip()
    return d.ref.name


def _missing(ctx: RuleContext) -> Iterator[Finding]:
    for d, facts, _ in _looked_up(ctx):
        if facts.exists is not False:
            continue
        registry = _REGISTRY[d.ref.ecosystem]
        where = "It is imported here, but no package.json declares it, and " if d.imported else ""
        message = (
            f"{where}{registry} has no package named {d.ref.name}. AI coding tools invent "
            "plausible package names, and attackers register them (slopsquatting): installing "
            "fails today and may fetch an attacker's code tomorrow. Use the package you meant, "
            "or remove it."
        )
        if d.imported:
            message = message[0].upper() + message[1:]
        yield finding(MISSING, d.location, message, _evidence(ctx, d))


def _days(delta: timedelta) -> str:
    days = max(delta.days, 0)
    return "1 day" if days == 1 else f"{days} days"


def _too_new(ctx: RuleContext) -> Iterator[Finding]:
    for d, facts, view in _looked_up(ctx):
        if facts.exists is not True or facts.popular:
            continue
        reasons: list[str] = []
        if facts.first_published is not None:
            age = view.now - facts.first_published
            if age < timedelta(days=view.min_age_days):
                reasons.append(f"was first published {_days(age)} ago")
        downloads = facts.weekly_downloads
        # PyPI publishes no reliable download counts; only npm's are a signal.
        if (
            d.ref.ecosystem is Ecosystem.NPM
            and downloads is not None
            and downloads < view.min_weekly_downloads
        ):
            reasons.append(f"had {downloads} downloads last week")
        if not reasons:
            continue
        message = (
            f"{d.ref.name} {' and '.join(reasons)} (limits: {view.min_age_days} days, "
            f"{view.min_weekly_downloads} weekly downloads). Brand-new and little-used names "
            "are where slopsquatting happens: someone registers a name AI tools invent. Check "
            "it is the package you meant and who publishes it."
        )
        yield finding(TOO_NEW, d.location, message, _evidence(ctx, d))


def _install_scripts(ctx: RuleContext) -> Iterator[Finding]:
    change = ctx.change
    if change is None:
        return  # an audit: every dependency is old news (ADR-004)
    texts = {f.path: f.text for f in ctx.files}
    for d, facts, _ in _looked_up(ctx):
        # An undeclared import isn't installed by this change.
        if d.imported or d.location.path not in texts or facts.install_scripts is None:
            continue
        scripts = [s for s in _INSTALL_HOOKS if s in facts.install_scripts]
        if not scripts or not added_in_change(d, change, texts[d.location.path]):
            continue
        kind = "script" if len(scripts) == 1 else "scripts"
        message = (
            f"{d.ref.name} runs its {', '.join(scripts)} {kind} when installed. This change "
            "adds it, so that code runs on every machine and CI job that installs "
            "dependencies. Read the script first, or install with --ignore-scripts."
        )
        yield finding(INSTALL_SCRIPTS, d.location, message, _evidence(ctx, d))


def _unverified(ctx: RuleContext) -> Iterator[Finding]:
    for d, facts, _ in _looked_up(ctx):
        if facts.exists is not None:
            continue
        message = (
            f"Couldn't check {d.ref.name} on {_REGISTRY[d.ref.ecosystem]}: "
            f"{facts.problem or 'no reason given'}. It was not verified; check it exists "
            "and is the package you meant before installing."
        )
        yield finding(DEPENDENCY_UNVERIFIED, d.location, message, _evidence(ctx, d))


RULES = (
    Rule(MISSING, _missing),
    Rule(TOO_NEW, _too_new),
    Rule(INSTALL_SCRIPTS, _install_scripts),
    Rule(DEPENDENCY_UNVERIFIED, _unverified),
)
