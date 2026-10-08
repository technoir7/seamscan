"""Claude Code hook (spec §11.4), pure half: hook input -> what to check -> hook response.

The CLI reads stdin, runs git and the scan, and prints what `respond` returns. Field names
follow the Claude Code hooks reference (code.claude.com/docs/en/hooks, checked 2026-10-08).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, cast

from seamscan.policy.verdict import Verdict
from seamscan.report.agent import render_agent

# The tools that write a file's text, with `tool_input.file_path`. NotebookEdit writes
# .ipynb, which seamscan doesn't analyze.
EDIT_TOOLS = frozenset({"Edit", "Write"})
EVENTS = ("PostToolUse", "PostToolBatch", "Stop")


class HookInputError(ValueError):
    pass


@dataclass(frozen=True)
class EditCheck:
    """After edits: check only the edited files. Paths are absolute, as Claude Code sends them."""

    event: str  # "PostToolUse" or "PostToolBatch"
    cwd: str
    paths: tuple[str, ...]


@dataclass(frozen=True)
class StopCheck:
    """At the end of a turn: check the working tree against HEAD."""

    cwd: str
    retry: bool  # stop_hook_active: Claude is already continuing because a Stop hook blocked


def _field(obj: dict[str, Any], name: str, kind: type, where: str = "hook input") -> Any:
    value = obj.get(name)
    if not isinstance(value, kind):
        raise HookInputError(f"{where}: `{name}` must be a {kind.__name__}")
    return value


def _object(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise HookInputError(f"{where} must be a JSON object")
    return cast(dict[str, Any], value)


def _edited_path(call: dict[str, Any], where: str) -> str | None:
    if call.get("tool_name") not in EDIT_TOOLS:
        return None
    tool_input = _object(call.get("tool_input"), f"{where} `tool_input`")
    return _field(tool_input, "file_path", str, f"{where} `tool_input`")


def read_input(raw: str) -> EditCheck | StopCheck:
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HookInputError(f"hook input is not JSON: {exc.msg} (line {exc.lineno})") from exc
    doc = _object(doc, "hook input")
    event = _field(doc, "hook_event_name", str)
    cwd = _field(doc, "cwd", str)
    if event == "PostToolUse":
        path = _edited_path(doc, "hook input")
        return EditCheck(event, cwd, (path,) if path else ())
    if event == "PostToolBatch":
        calls = _field(doc, "tool_calls", list)
        paths = {
            p
            for i, call in enumerate(calls)
            if (p := _edited_path(_object(call, f"tool_calls[{i}]"), f"tool_calls[{i}]"))
        }
        return EditCheck(event, cwd, tuple(sorted(paths)))
    if event == "Stop":
        return StopCheck(cwd, _field(doc, "stop_hook_active", bool))
    raise HookInputError(f"event {event!r} isn't handled; configure {', '.join(EVENTS)}")


def _dump(doc: dict[str, Any]) -> str:
    return json.dumps(doc, ensure_ascii=False, sort_keys=True)


def respond(plan: EditCheck | StopCheck, verdict: Verdict) -> str | None:
    """The hook's stdout, or None to stay silent. Only blocking findings reach the agent."""
    if verdict.blocking:
        text = render_agent(verdict, blocking_only=True)
        if isinstance(plan, EditCheck):
            # Context, not a block: the edit already happened and the agent can fix it.
            return _dump(
                {"hookSpecificOutput": {"hookEventName": plan.event, "additionalContext": text}}
            )
        if plan.retry:
            # Blocking again could loop; leave the decision to the user.
            return _dump({"systemMessage": text})
        return _dump({"decision": "block", "reason": text})
    if verdict.internal_errors:
        return _dump({"systemMessage": f"seamscan: {verdict.headline}"})
    return None
