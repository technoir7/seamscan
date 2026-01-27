#!/usr/bin/env python3
"""
ClogBot: Deterministic, epistemically adversarial hardener for vibe-coded repositories.

This tool runs truth-generating checks, ranks failures, and emits structured artifacts
for LLM-assisted fixes. It is strictly deterministic with NO auto-fixing capabilities.

Doctrine: AI-assisted code is guilty until proven safe. Trust evidence, not plausibility.
"""

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import typer

# =============================================================================
# SEVERITY LEVELS (STRICT ORDERING)
# =============================================================================


class Severity(IntEnum):
    """Failure severity levels in strict priority order."""

    BUILD_SYNTAX = 1  # Build / syntax errors
    DEPENDENCY = 2  # Dependency integrity or audit failures
    SUSPICIOUS_IMPORT = 3  # Unresolved or suspicious imports (hallucinated libraries)
    TYPECHECK = 4  # Type errors
    TEST = 5  # Test failures
    LINT_FORMAT = 6  # Lint / format issues
    HEURISTIC = 7  # Heuristic warnings


# =============================================================================
# DATA STRUCTURES
# =============================================================================


@dataclass
class CheckResult:
    """Result of a deterministic check."""

    name: str
    passed: bool
    severity: Severity
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    command: str = ""
    error_message: str = ""


@dataclass
class HeuristicWarning:
    """A heuristic red flag detected in the codebase."""

    message: str
    severity: Severity = Severity.HEURISTIC
    file_path: Optional[str] = None
    line_number: Optional[int] = None


@dataclass
class StackInfo:
    """Detected stack information."""

    has_python: bool = False
    has_node: bool = False
    has_typescript: bool = False
    python_venv_active: bool = False
    has_pytest: bool = False
    has_npm_test: bool = False
    has_npm_lint: bool = False
    has_npm_typecheck: bool = False


@dataclass
class GitDiffMeta:
    """Git diff metadata."""

    files_changed: List[str] = field(default_factory=list)
    loc_added: int = 0
    loc_removed: int = 0
    directories_touched: List[str] = field(default_factory=list)
    dependency_changes: List[str] = field(default_factory=list)


# =============================================================================
# STACK DETECTION
# =============================================================================


def detect_stack(base_path: Path) -> StackInfo:
    """Auto-detect project stack based on marker files."""
    info = StackInfo()

    # Python detection
    if (base_path / "pyproject.toml").exists() or any(
        (base_path / f).exists() for f in ["requirements.txt", "requirements-dev.txt"]
    ):
        info.has_python = True
        info.python_venv_active = os.environ.get("VIRTUAL_ENV") is not None

        # Check for pytest
        try:
            subprocess.run(
                ["pytest", "--version"],
                capture_output=True,
                timeout=5,
                cwd=base_path,
            )
            info.has_pytest = True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    # Node detection
    package_json = base_path / "package.json"
    if package_json.exists():
        info.has_node = True
        try:
            with open(package_json) as f:
                pkg_data = json.load(f)
                scripts = pkg_data.get("scripts", {})
                info.has_npm_test = "test" in scripts
                info.has_npm_lint = "lint" in scripts
                info.has_npm_typecheck = "typecheck" in scripts
        except (json.JSONDecodeError, IOError):
            pass

    # TypeScript detection
    if (base_path / "tsconfig.json").exists():
        info.has_typescript = True

    return info


# =============================================================================
# DETERMINISTIC CHECKS
# =============================================================================


def run_check(
    command: List[str],
    name: str,
    severity: Severity,
    cwd: Path,
    timeout: int = 300,
) -> CheckResult:
    """Run a deterministic check and capture output."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout,
        )
        passed = result.returncode == 0
        return CheckResult(
            name=name,
            passed=passed,
            severity=severity,
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.returncode,
            command=" ".join(command),
        )
    except subprocess.TimeoutExpired:
        return CheckResult(
            name=name,
            passed=False,
            severity=severity,
            error_message=f"Command timed out after {timeout}s",
            command=" ".join(command),
        )
    except FileNotFoundError:
        return CheckResult(
            name=name,
            passed=False,
            severity=severity,
            error_message=f"Command not found: {command[0]}",
            command=" ".join(command),
        )


def run_python_checks(stack: StackInfo, base_path: Path) -> List[CheckResult]:
    """Run Python-specific checks."""
    checks = []

    if not stack.has_python:
        return checks

    # 1. Syntax check with compileall
    checks.append(
        run_check(
            [sys.executable, "-m", "compileall", ".", "-q"],
            "Python Syntax (compileall)",
            Severity.BUILD_SYNTAX,
            base_path,
        )
    )

    # 2. Dependency integrity
    if stack.python_venv_active:
        checks.append(
            run_check(
                [sys.executable, "-m", "pip", "check"],
                "Python Dependencies (pip check)",
                Severity.DEPENDENCY,
                base_path,
            )
        )

    # 3. Ruff linting
    checks.append(
        run_check(
            ["ruff", "check", "."],
            "Python Lint (ruff)",
            Severity.LINT_FORMAT,
            base_path,
        )
    )

    # 4. Ruff formatting
    checks.append(
        run_check(
            ["ruff", "format", "--check", "."],
            "Python Format (ruff)",
            Severity.LINT_FORMAT,
            base_path,
        )
    )

    # 5. Tests
    if stack.has_pytest:
        checks.append(
            run_check(
                ["pytest", "-q"],
                "Python Tests (pytest)",
                Severity.TEST,
                base_path,
            )
        )

    # 6. Security audit
    checks.append(
        run_check(
            ["pip-audit"],
            "Python Security Audit (pip-audit)",
            Severity.DEPENDENCY,
            base_path,
        )
    )

    return checks


def run_node_checks(stack: StackInfo, base_path: Path) -> List[CheckResult]:
    """Run Node/JavaScript/TypeScript checks."""
    checks = []

    if not stack.has_node:
        return checks

    # 1. npm test (if defined)
    if stack.has_npm_test:
        checks.append(
            run_check(
                ["npm", "test"],
                "Node Tests (npm test)",
                Severity.TEST,
                base_path,
            )
        )

    # 2. npm run lint (if defined)
    if stack.has_npm_lint:
        checks.append(
            run_check(
                ["npm", "run", "lint"],
                "Node Lint (npm run lint)",
                Severity.LINT_FORMAT,
                base_path,
            )
        )

    # 3. npm run typecheck (if defined) OR fallback to tsc
    if stack.has_npm_typecheck:
        checks.append(
            run_check(
                ["npm", "run", "typecheck"],
                "TypeScript Check (npm run typecheck)",
                Severity.TYPECHECK,
                base_path,
            )
        )
    elif stack.has_typescript:
        checks.append(
            run_check(
                ["npx", "tsc", "-p", "tsconfig.json", "--noEmit"],
                "TypeScript Check (tsc)",
                Severity.TYPECHECK,
                base_path,
            )
        )

    # 4. Security audit
    checks.append(
        run_check(
            ["npm", "audit", "--audit-level=high"],
            "Node Security Audit (npm audit)",
            Severity.DEPENDENCY,
            base_path,
        )
    )

    return checks


def extract_python_imports_from_diff(diff_content: str) -> List[str]:
    """Extract new Python imports from git diff."""
    imports = set()
    # Match: from X import Y, import X, import X as Y
    import_patterns = [
        re.compile(r"^\+(?:from|import)\s+([a-zA-Z_][a-zA-Z0-9_]*)", re.MULTILINE),
    ]
    for pattern in import_patterns:
        for match in pattern.finditer(diff_content):
            module = match.group(1)
            # Filter out relative imports and common builtins
            if module and not module.startswith("."):
                imports.add(module)
    return list(imports)


def extract_node_imports_from_diff(diff_content: str) -> List[str]:
    """Extract new Node require/import statements from git diff."""
    imports = set()
    # Match: require('X'), require("X"), import X from 'Y', import 'X'
    import_patterns = [
        re.compile(r"^\+.*require\(['\"]([^'\"]+)['\"]\)", re.MULTILINE),
        re.compile(r"^\+.*import\s+.*?from\s+['\"]([^'\"]+)['\"]", re.MULTILINE),
        re.compile(r"^\+.*import\s+['\"]([^'\"]+)['\"]", re.MULTILINE),
    ]
    for pattern in import_patterns:
        for match in pattern.finditer(diff_content):
            module = match.group(1)
            # Filter out relative imports
            if module and not module.startswith("."):
                imports.add(module)
    return list(imports)


def validate_python_imports(
    imports: List[str], base_path: Path
) -> List[CheckResult]:
    """Validate that Python imports can be resolved."""
    checks = []
    for module in imports:
        result = subprocess.run(
            [sys.executable, "-c", f"import {module}"],
            capture_output=True,
            text=True,
            cwd=base_path,
            timeout=5,
        )
        if result.returncode != 0:
            checks.append(
                CheckResult(
                    name=f"Python Import Validation ({module})",
                    passed=False,
                    severity=Severity.SUSPICIOUS_IMPORT,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    exit_code=result.returncode,
                    command=f"python -c 'import {module}'",
                    error_message=f"Suspicious import: '{module}' cannot be resolved (possible hallucinated library)",
                )
            )
    return checks


def validate_node_imports(imports: List[str], base_path: Path) -> List[CheckResult]:
    """Validate that Node imports can be resolved."""
    checks = []
    for module in imports:
        result = subprocess.run(
            ["node", "-e", f"require('{module}')"],
            capture_output=True,
            text=True,
            cwd=base_path,
            timeout=5,
        )
        if result.returncode != 0:
            checks.append(
                CheckResult(
                    name=f"Node Import Validation ({module})",
                    passed=False,
                    severity=Severity.SUSPICIOUS_IMPORT,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    exit_code=result.returncode,
                    command=f"node -e \"require('{module}')\"",
                    error_message=f"Suspicious import: '{module}' cannot be resolved (possible hallucinated library)",
                )
            )
    return checks


# =============================================================================
# GIT DIFF ANALYSIS
# =============================================================================


def get_git_diff_meta(base_path: Path) -> GitDiffMeta:
    """Extract git diff metadata."""
    meta = GitDiffMeta()

    try:
        # Get files changed
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            cwd=base_path,
            timeout=10,
        )
        if result.returncode == 0:
            meta.files_changed = [f for f in result.stdout.strip().split("\n") if f]

        # Get staged files too
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            cwd=base_path,
            timeout=10,
        )
        if result.returncode == 0:
            staged = [f for f in result.stdout.strip().split("\n") if f]
            meta.files_changed.extend(staged)
            meta.files_changed = list(set(meta.files_changed))  # Deduplicate

        # Get LOC stats
        result = subprocess.run(
            ["git", "diff", "--numstat", "HEAD"],
            capture_output=True,
            text=True,
            cwd=base_path,
            timeout=10,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split("\t")
                    if len(parts) >= 2:
                        try:
                            meta.loc_added += int(parts[0]) if parts[0] != "-" else 0
                            meta.loc_removed += int(parts[1]) if parts[1] != "-" else 0
                        except ValueError:
                            pass

        # Extract directories
        meta.directories_touched = list(
            set(str(Path(f).parent) for f in meta.files_changed if f)
        )

        # Check for dependency changes
        dep_files = [
            "requirements.txt",
            "requirements-dev.txt",
            "pyproject.toml",
            "package.json",
            "package-lock.json",
            "yarn.lock",
            "pnpm-lock.yaml",
        ]
        meta.dependency_changes = [f for f in meta.files_changed if f in dep_files]

    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return meta


def get_git_diff_content(base_path: Path) -> str:
    """Get the full git diff for heuristic analysis."""
    try:
        result = subprocess.run(
            ["git", "diff", "HEAD"],
            capture_output=True,
            text=True,
            cwd=base_path,
            timeout=30,
        )
        if result.returncode == 0:
            return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return ""


# =============================================================================
# HEURISTIC RED FLAGS
# =============================================================================


HIGH_RISK_PATHS = [
    "auth",
    "authentication",
    "payment",
    "payments",
    "db",
    "database",
    "migration",
    "migrations",
    "config",
    "settings",
]


def detect_heuristic_warnings(
    diff_meta: GitDiffMeta,
    diff_content: str,
    max_diff_loc: Optional[int],
) -> List[HeuristicWarning]:
    """Detect heuristic red flags in the codebase."""
    warnings = []

    # 1. TODO/FIXME/HACK/XXX in diff
    todo_pattern = re.compile(r"^\+.*\b(TODO|FIXME|HACK|XXX)\b", re.MULTILINE | re.IGNORECASE)
    for match in todo_pattern.finditer(diff_content):
        warnings.append(
            HeuristicWarning(
                message=f"Code comment marker found in diff: {match.group(0).strip()}"
            )
        )

    # 2. Bare except / swallowed errors
    bare_except_pattern = re.compile(r"^\+.*except\s*:", re.MULTILINE)
    for match in bare_except_pattern.finditer(diff_content):
        warnings.append(
            HeuristicWarning(message=f"Bare except clause detected: {match.group(0).strip()}")
        )

    # 3. Placeholder bodies
    placeholder_patterns = [
        re.compile(r"^\+.*:\s*pass\s*$", re.MULTILINE),
        re.compile(r"^\+.*return\s+None\s*$", re.MULTILINE),
    ]
    for pattern in placeholder_patterns:
        for match in pattern.finditer(diff_content):
            warnings.append(
                HeuristicWarning(
                    message=f"Placeholder body detected in changed code: {match.group(0).strip()}"
                )
            )

    # 4. LOC threshold
    if max_diff_loc is not None:
        total_loc = diff_meta.loc_added + diff_meta.loc_removed
        if total_loc > max_diff_loc:
            warnings.append(
                HeuristicWarning(
                    message=f"Diff exceeds LOC threshold: {total_loc} > {max_diff_loc}"
                )
            )

    # 5. Dependency changes without lockfile updates
    if diff_meta.dependency_changes:
        has_manifest = any(
            f in diff_meta.dependency_changes
            for f in ["requirements.txt", "pyproject.toml", "package.json"]
        )
        has_lockfile = any(
            f in diff_meta.dependency_changes
            for f in ["package-lock.json", "yarn.lock", "pnpm-lock.yaml"]
        )
        if has_manifest and not has_lockfile:
            warnings.append(
                HeuristicWarning(
                    message="Dependency manifest changed without lockfile update"
                )
            )

    # 6. High-risk path edits
    for file_path in diff_meta.files_changed:
        file_lower = file_path.lower()
        for risk_path in HIGH_RISK_PATHS:
            if risk_path in file_lower:
                warnings.append(
                    HeuristicWarning(
                        message=f"High-risk path edited: {file_path} (contains '{risk_path}')",
                        file_path=file_path,
                    )
                )
                break

    # === TAXONOMY-BASED VULNERABILITY CHECKS ===

    # Class 1: Supply-Chain Confusion - Floating versions
    floating_version_pattern = re.compile(
        r'^\+.*["\'](\*|latest|\^0\.|~0\.|>=|>)["\']', re.MULTILINE
    )
    for match in floating_version_pattern.finditer(diff_content):
        warnings.append(
            HeuristicWarning(
                message=f"[CLASS-1] Floating dependency version: {match.group(0).strip()} (supply-chain risk)"
            )
        )

    # Class 3: Install/Build-Time Execution - postinstall hooks
    postinstall_pattern = re.compile(
        r'^\+.*"(preinstall|install|postinstall)"\s*:', re.MULTILINE
    )
    for match in postinstall_pattern.finditer(diff_content):
        warnings.append(
            HeuristicWarning(
                message=f"[CLASS-3] Install-time script: {match.group(0).strip()} (execution before runtime controls)"
            )
        )

    # Class 4: Copy/Paste Command Injection - pipe-to-shell
    pipe_to_shell_pattern = re.compile(
        r'^\+.*(curl|wget).*\|\s*(sh|bash|zsh|powershell|iex)', re.MULTILINE
    )
    for match in pipe_to_shell_pattern.finditer(diff_content):
        warnings.append(
            HeuristicWarning(
                message=f"[CLASS-4] Pipe-to-shell: {match.group(0).strip()} (command injection risk)"
            )
        )

    # Class 4: Dangerous shell operators (only warn if excessive)
    dangerous_shell_pattern = re.compile(
        r'^\+.*(&&|\|\||;|\$\(|`[^`]+`).*', re.MULTILINE
    )
    shell_operator_matches = list(dangerous_shell_pattern.finditer(diff_content))
    if len(shell_operator_matches) > 5:
        warnings.append(
            HeuristicWarning(
                message=f"[CLASS-4] Multiple dangerous shell operators ({len(shell_operator_matches)} instances)"
            )
        )

    # Class 5: Tool/Repo Configuration Poisoning - AI config changes
    ai_config_files = [".cursor/rules", ".cursorrules", ".aider", ".copilot-instructions"]
    for file_path in diff_meta.files_changed:
        if any(cfg in file_path for cfg in ai_config_files):
            warnings.append(
                HeuristicWarning(
                    message=f"[CLASS-5] AI tool config modified: {file_path} (control-plane backdoor risk)",
                    file_path=file_path,
                )
            )

    # Class 5: Unicode control characters
    unicode_control_pattern = re.compile(r'[\u200b-\u200f\u202a-\u202e\u2060-\u206f]')
    if unicode_control_pattern.search(diff_content):
        warnings.append(
            HeuristicWarning(
                message="[CLASS-5] Invisible Unicode control characters detected (obfuscation risk)"
            )
        )

    # Class 6: Prompt Injection via Context - instruction patterns
    prompt_injection_pattern = re.compile(
        r'^\+.*(ignore previous|system prompt|you are|exfiltrate|print env)', 
        re.MULTILINE | re.IGNORECASE
    )
    for match in prompt_injection_pattern.finditer(diff_content):
        warnings.append(
            HeuristicWarning(
                message=f"[CLASS-6] Prompt injection pattern: {match.group(0).strip()[:60]}... (context poisoning)"
            )
        )

    # Class 7: Secret Material - high entropy strings
    high_entropy_pattern = re.compile(r'^\+.*["\']([A-Za-z0-9+/=]{40,})["\']', re.MULTILINE)
    for match in high_entropy_pattern.finditer(diff_content):
        literal = match.group(1)
        # Simple Shannon entropy approximation
        if len(set(literal)) / len(literal) > 0.7:
            warnings.append(
                HeuristicWarning(
                    message=f"[CLASS-7] High-entropy literal (potential secret): {literal[:20]}..."
                )
            )

    # Class 7: Token patterns
    token_patterns = [
        (r'AKIA[0-9A-Z]{16}', "AWS Access Key"),
        (r'eyJ[A-Za-z0-9-_]+\.eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+', "JWT Token"),
        (r'-----BEGIN [A-Z ]+-----', "PEM Block"),
        (r'ghp_[A-Za-z0-9]{36}', "GitHub PAT"),
        (r'sk-[A-Za-z0-9]{48}', "OpenAI Key"),
    ]
    for pattern, name in token_patterns:
        if re.search(pattern, diff_content):
            warnings.append(
                HeuristicWarning(
                    message=f"[CLASS-7] {name} pattern detected (credential exposure)"
                )
            )

    # Class 7: Forbidden files
    forbidden_files = [".env", ".pem", "id_rsa", "credentials", ".p12", "kubeconfig"]
    for file_path in diff_meta.files_changed:
        for forbidden in forbidden_files:
            if forbidden in file_path.lower():
                warnings.append(
                    HeuristicWarning(
                        message=f"[CLASS-7] Forbidden file: {file_path} (credential exposure)",
                        file_path=file_path,
                    )
                )

    # Class 2: Weak crypto primitives
    weak_crypto_pattern = re.compile(
        r'^\+.*(MD5|SHA1|DES|RC4|ECB)\s*\(', re.MULTILINE
    )
    for match in weak_crypto_pattern.finditer(diff_content):
        warnings.append(
            HeuristicWarning(
                message=f"[CLASS-2] Weak crypto primitive: {match.group(0).strip()}"
            )
        )

    # Class 2: Missing auth decorators (simplified heuristic)
    admin_route_pattern = re.compile(
        r'^\+.*(@(app\.route|api\.route)|router\.(get|post|put|delete))\s*\(["\']/(admin|billing|internal)', 
        re.MULTILINE
    )
    for match in admin_route_pattern.finditer(diff_content):
        match_pos = match.start()
        context = diff_content[max(0, match_pos - 300):match_pos]
        if not re.search(r'@(require_auth|login_required|authenticated|check_auth)', context):
            warnings.append(
                HeuristicWarning(
                    message=f"[CLASS-2] Sensitive route without auth decorator: {match.group(0).strip()[:60]}..."
                )
            )

    # Class 10: Shared mutable state in async
    async_global_pattern = re.compile(
        r'^\+\s*global\s+\w+', re.MULTILINE
    )
    if async_global_pattern.search(diff_content) and 'async def' in diff_content:
        warnings.append(
            HeuristicWarning(
                message="[CLASS-10] Global state mutation in async context (race condition risk)"
            )
        )

    # Class 11: Production endpoints in configs
    prod_pattern = re.compile(
        r'^\+.*\.prod|production|prd|aws\.amazon|azure\.microsoft|cloud\.google', 
        re.MULTILINE | re.IGNORECASE
    )
    for match in prod_pattern.finditer(diff_content):
        for file_path in diff_meta.files_changed:
            if any(cfg in file_path.lower() for cfg in ["config", ".env", "settings"]):
                warnings.append(
                    HeuristicWarning(
                        message=f"[CLASS-11] Production endpoint in config: {match.group(0).strip()[:50]}...",
                        file_path=file_path,
                    )
                )
                break

    # Class 11: Destructive commands
    destructive_pattern = re.compile(
        r'^\+.*(DROP\s+TABLE|DELETE\s+FROM|rm\s+-rf|terraform\s+destroy)', 
        re.MULTILINE | re.IGNORECASE
    )
    for match in destructive_pattern.finditer(diff_content):
        warnings.append(
            HeuristicWarning(
                message=f"[CLASS-11] Destructive command: {match.group(0).strip()} (requires approval)"
            )
        )

    return warnings


# =============================================================================
# OUTPUT GENERATION
# =============================================================================


def generate_verdict_md(
    checks: List[CheckResult],
    warnings: List[HeuristicWarning],
    output_dir: Path,
) -> None:
    """Generate verdict.md with ranked failures."""
    failures = [c for c in checks if not c.passed]
    failures.sort(key=lambda x: x.severity)

    lines = ["# ClogBot Verdict\n"]

    if not failures and not warnings:
        lines.append("## ✅ All Checks Passed\n")
        lines.append("No blocking failures detected.\n")
    else:
        lines.append("## ❌ Failures Detected\n")

        # Group by severity
        for severity in Severity:
            severity_failures = [f for f in failures if f.severity == severity]
            if severity_failures:
                lines.append(f"\n### Severity {severity.value}: {severity.name}\n")
                for failure in severity_failures:
                    lines.append(f"- **{failure.name}** (exit code: {failure.exit_code})\n")
                    if failure.error_message:
                        lines.append(f"  - Error: {failure.error_message}\n")

        # Warnings
        if warnings:
            lines.append(f"\n### Severity {Severity.HEURISTIC.value}: Heuristic Warnings\n")
            for warning in warnings:
                lines.append(f"- {warning.message}\n")

    with open(output_dir / "verdict.md", "w") as f:
        f.writelines(lines)


def generate_diff_meta_json(diff_meta: GitDiffMeta, output_dir: Path) -> None:
    """Generate diff_meta.json."""
    data = {
        "files_changed": diff_meta.files_changed,
        "loc_added": diff_meta.loc_added,
        "loc_removed": diff_meta.loc_removed,
        "directories_touched": diff_meta.directories_touched,
        "dependency_changes": diff_meta.dependency_changes,
    }
    with open(output_dir / "diff_meta.json", "w") as f:
        json.dump(data, f, indent=2)


def generate_evidence_files(checks: List[CheckResult], output_dir: Path) -> None:
    """Generate evidence files for each check type."""
    evidence_dir = output_dir / "evidence"
    evidence_dir.mkdir(exist_ok=True)

    # Group checks by type
    evidence_map = {
        "tests.txt": [c for c in checks if c.severity == Severity.TEST],
        "lint.txt": [c for c in checks if c.severity == Severity.LINT_FORMAT],
        "typecheck.txt": [c for c in checks if c.severity == Severity.TYPECHECK],
        "deps.txt": [c for c in checks if c.severity == Severity.DEPENDENCY],
        "security.txt": [c for c in checks if c.severity == Severity.SUSPICIOUS_IMPORT],
        "build.txt": [c for c in checks if c.severity == Severity.BUILD_SYNTAX],
    }

    for filename, check_list in evidence_map.items():
        if check_list:
            with open(evidence_dir / filename, "w") as f:
                for check in check_list:
                    f.write(f"{'='*80}\n")
                    f.write(f"CHECK: {check.name}\n")
                    f.write(f"COMMAND: {check.command}\n")
                    f.write(f"EXIT CODE: {check.exit_code}\n")
                    f.write(f"PASSED: {check.passed}\n")
                    f.write(f"{'='*80}\n\n")
                    if check.error_message:
                        f.write(f"ERROR: {check.error_message}\n\n")
                    if check.stdout:
                        f.write("STDOUT:\n")
                        f.write(check.stdout)
                        f.write("\n\n")
                    if check.stderr:
                        f.write("STDERR:\n")
                        f.write(check.stderr)
                        f.write("\n\n")


def truncate_output(text: str, max_lines: int = 200) -> str:
    """Truncate output to max lines."""
    lines = text.split("\n")
    if len(lines) <= max_lines:
        return text
    return "\n".join(lines[:max_lines]) + f"\n\n... (truncated {len(lines) - max_lines} lines)"


def generate_handoff_prompt(
    checks: List[CheckResult],
    warnings: List[HeuristicWarning],
    diff_meta: GitDiffMeta,
    output_dir: Path,
) -> None:
    """Generate handoff_prompt.md for LLM consumption."""
    failures = [c for c in checks if not c.passed]
    failures.sort(key=lambda x: x.severity)

    lines = ["# ClogBot Handoff Prompt\n\n"]

    # Explicit instruction
    lines.append("## Instructions\n\n")
    lines.append("**Fix ONLY blocking failures using minimal diffs. No refactors.**\n\n")

    # Summary
    lines.append("## Summary\n\n")
    if failures or warnings:
        lines.append(f"- **{len(failures)}** deterministic check failures\n")
        lines.append(f"- **{len(warnings)}** heuristic warnings\n")
        lines.append(f"- **{len(diff_meta.files_changed)}** files changed\n")
        lines.append(f"- **+{diff_meta.loc_added}** / **-{diff_meta.loc_removed}** LOC\n\n")
    else:
        lines.append("All checks passed. No action required.\n\n")
        with open(output_dir / "handoff_prompt.md", "w") as f:
            f.writelines(lines)
        return

    # Ranked failures
    lines.append("## Ranked Failures\n\n")
    for i, failure in enumerate(failures, 1):
        lines.append(f"### {i}. {failure.name} (Severity {failure.severity.value})\n\n")
        lines.append(f"**Command:** `{failure.command}`\n\n")
        lines.append(f"**Exit Code:** {failure.exit_code}\n\n")
        if failure.error_message:
            lines.append(f"**Error:** {failure.error_message}\n\n")

        # Include bounded output
        if failure.stdout:
            lines.append("**Output:**\n```\n")
            lines.append(truncate_output(failure.stdout, 100))
            lines.append("\n```\n\n")
        if failure.stderr:
            lines.append("**Errors:**\n```\n")
            lines.append(truncate_output(failure.stderr, 100))
            lines.append("\n```\n\n")

    # Warnings
    if warnings:
        lines.append("## Heuristic Warnings\n\n")
        for warning in warnings:
            lines.append(f"- {warning.message}\n")
        lines.append("\n")

    # Relevant files
    lines.append("## Relevant Files\n\n")
    if diff_meta.files_changed:
        for file_path in sorted(diff_meta.files_changed):
            lines.append(f"- `{file_path}`\n")
    else:
        lines.append("No changed files detected.\n")
    lines.append("\n")

    # Reproduction commands
    lines.append("## Reproduction Commands\n\n")
    lines.append("Run these commands to reproduce failures:\n\n")
    lines.append("```bash\n")
    for failure in failures:
        lines.append(f"# {failure.name}\n")
        lines.append(f"{failure.command}\n\n")
    lines.append("```\n")

    with open(output_dir / "handoff_prompt.md", "w") as f:
        f.writelines(lines)


# =============================================================================
# MAIN CLI
# =============================================================================

app = typer.Typer(help="ClogBot: Deterministic hardener for vibe-coded repositories")


@app.command()
def check(
    out: Path = typer.Option(
        Path("./clogbot_output"),
        "--out",
        help="Output directory for results",
    ),
    fail_on_warn: bool = typer.Option(
        False,
        "--fail-on-warn",
        help="Exit with non-zero code on warnings",
    ),
    max_diff_loc: Optional[int] = typer.Option(
        None,
        "--max-diff-loc",
        help="Maximum allowed diff LOC (triggers warning if exceeded)",
    ),
) -> None:
    """Run deterministic checks and generate structured output."""
    base_path = Path.cwd()

    typer.echo("🔍 ClogBot: Epistemically Adversarial Hardening")
    typer.echo(f"📂 Working directory: {base_path}")
    typer.echo("")

    # 1. Detect stack
    typer.echo("🔎 Detecting stack...")
    stack = detect_stack(base_path)
    typer.echo(f"  Python: {stack.has_python}")
    typer.echo(f"  Node: {stack.has_node}")
    typer.echo(f"  TypeScript: {stack.has_typescript}")
    typer.echo("")

    # 2. Run deterministic checks
    typer.echo("⚙️  Running deterministic checks...")
    all_checks: List[CheckResult] = []
    all_checks.extend(run_python_checks(stack, base_path))
    all_checks.extend(run_node_checks(stack, base_path))

    passed_count = sum(1 for c in all_checks if c.passed)
    failed_count = len(all_checks) - passed_count
    typer.echo(f"  ✅ {passed_count} passed")
    typer.echo(f"  ❌ {failed_count} failed")
    typer.echo("")

    # 3. Git diff analysis
    typer.echo("📊 Analyzing git diff...")
    diff_meta = get_git_diff_meta(base_path)
    diff_content = get_git_diff_content(base_path)
    typer.echo(f"  Files changed: {len(diff_meta.files_changed)}")
    typer.echo(f"  LOC: +{diff_meta.loc_added} / -{diff_meta.loc_removed}")
    typer.echo("")

    # 4. Import validation (security check for hallucinated libraries)
    typer.echo("🔒 Validating imports...")
    import_checks: List[CheckResult] = []
    if stack.has_python and diff_content:
        python_imports = extract_python_imports_from_diff(diff_content)
        if python_imports:
            typer.echo(f"  Checking {len(python_imports)} Python imports...")
            try:
                import_checks.extend(validate_python_imports(python_imports, base_path))
            except Exception:
                pass  # Don't crash on validation errors
    if stack.has_node and diff_content:
        node_imports = extract_node_imports_from_diff(diff_content)
        if node_imports:
            typer.echo(f"  Checking {len(node_imports)} Node imports...")
            try:
                import_checks.extend(validate_node_imports(node_imports, base_path))
            except Exception:
                pass  # Don't crash on validation errors
    
    all_checks.extend(import_checks)
    suspicious_import_count = len([c for c in import_checks if not c.passed])
    if suspicious_import_count > 0:
        typer.echo(f"  ⚠️  {suspicious_import_count} suspicious imports detected")
    else:
        typer.echo(f"  ✅ All imports validated")
    typer.echo("")

    # 5. Heuristic warnings
    typer.echo("⚠️  Detecting heuristic warnings...")
    warnings = detect_heuristic_warnings(diff_meta, diff_content, max_diff_loc)
    typer.echo(f"  Found {len(warnings)} warnings")
    typer.echo("")

    # 5. Generate output
    typer.echo(f"📝 Generating output in {out}...")
    out.mkdir(parents=True, exist_ok=True)

    generate_verdict_md(all_checks, warnings, out)
    generate_diff_meta_json(diff_meta, out)
    generate_evidence_files(all_checks, out)
    generate_handoff_prompt(all_checks, warnings, diff_meta, out)

    typer.echo("✅ Output generated:")
    typer.echo(f"  - {out / 'verdict.md'}")
    typer.echo(f"  - {out / 'diff_meta.json'}")
    typer.echo(f"  - {out / 'evidence/'}")
    typer.echo(f"  - {out / 'handoff_prompt.md'}")
    typer.echo("")

    # 6. Exit code
    has_failures = failed_count > 0
    has_warnings = len(warnings) > 0

    if has_failures:
        typer.echo("❌ VERDICT: BLOCKING FAILURES DETECTED", err=True)
        raise typer.Exit(code=1)
    elif has_warnings and fail_on_warn:
        typer.echo("⚠️  VERDICT: WARNINGS DETECTED (--fail-on-warn)", err=True)
        raise typer.Exit(code=2)
    else:
        typer.echo("✅ VERDICT: ALL CHECKS PASSED")
        raise typer.Exit(code=0)


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
