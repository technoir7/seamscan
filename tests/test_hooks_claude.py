"""Spec §11.4: the Claude Code hook's pure half, from hook input to hook response."""

import json

import pytest

from seamscan.hooks.claude import EditCheck, HookInputError, StopCheck, read_input, respond
from seamscan.model import Confidence, Finding, Location, Severity
from seamscan.policy.verdict import Policy, decide


def hook_input(**fields: object) -> str:
    return json.dumps({"session_id": "s", "cwd": "/repo", **fields})


def post_tool_use(tool: str = "Edit", path: str = "/repo/app.py") -> str:
    return hook_input(
        hook_event_name="PostToolUse",
        tool_name=tool,
        tool_input={"file_path": path, "old_string": "a", "new_string": "b"},
        tool_response={"filePath": path},
    )


def stop(active: bool = False) -> str:
    return hook_input(hook_event_name="Stop", stop_hook_active=active)


BLOCKING = decide(
    [
        Finding(
            "SC-CODE-001",
            Severity.HIGH,
            Confidence.HIGH,
            Location("app.py", 2, 1, 2, 9),
            "`requests.get` called with verify=False",
            "",
        )
    ],
    Policy(),
)
NOTE_ONLY = decide(
    [
        Finding(
            "SC-CODE-002", Severity.MEDIUM, Confidence.HIGH, Location("a.py", 1, 1, 1, 2), "m", ""
        )
    ],
    Policy(),
)
CLEAN = decide([], Policy())
CRASHED = decide(
    [
        Finding(
            "SC-META-003",
            Severity.LOW,
            Confidence.HIGH,
            Location("<rule SC-X>", 1, 1, 1, 1),
            "SC-X crashed",
            "",
        )
    ],
    Policy(),
)


# --- reading the input -------------------------------------------------------------


def test_post_tool_use_on_an_edit_tool_checks_that_file():
    assert read_input(post_tool_use("Write")) == EditCheck(
        "PostToolUse", "/repo", ("/repo/app.py",)
    )


def test_post_tool_use_on_another_tool_checks_nothing():
    plan = read_input(post_tool_use("Read"))
    assert plan == EditCheck("PostToolUse", "/repo", ())


def test_post_tool_batch_collects_every_edited_file_once():
    raw = hook_input(
        hook_event_name="PostToolBatch",
        tool_calls=[
            {"tool_name": "Edit", "tool_input": {"file_path": "/repo/b.py"}},
            {"tool_name": "Read", "tool_input": {"file_path": "/repo/r.py"}},
            {"tool_name": "Write", "tool_input": {"file_path": "/repo/a.py"}},
            {"tool_name": "Edit", "tool_input": {"file_path": "/repo/b.py"}},
            {"tool_name": "Bash", "tool_input": {"command": "ls"}},
        ],
    )
    assert read_input(raw) == EditCheck("PostToolBatch", "/repo", ("/repo/a.py", "/repo/b.py"))


def test_stop_carries_stop_hook_active():
    assert read_input(stop()) == StopCheck("/repo", retry=False)
    assert read_input(stop(active=True)) == StopCheck("/repo", retry=True)


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "not json",
        "[1, 2]",
        json.dumps({"hook_event_name": "Stop", "stop_hook_active": False}),  # no cwd
        hook_input(stop_hook_active=False),  # no event
        hook_input(hook_event_name="Stop"),  # no stop_hook_active
        hook_input(hook_event_name="Stop", stop_hook_active="yes"),
        hook_input(hook_event_name="PostToolUse", tool_name="Edit", tool_input={}),
        hook_input(hook_event_name="PostToolUse", tool_name="Edit"),
        hook_input(hook_event_name="PostToolBatch", tool_calls={}),
        hook_input(hook_event_name="PostToolBatch", tool_calls=[{"tool_name": "Edit"}]),
        hook_input(hook_event_name="SessionStart"),
    ],
)
def test_malformed_or_unsupported_input_is_an_error(raw: str):
    with pytest.raises(HookInputError):
        read_input(raw)


def test_unsupported_event_names_the_supported_ones():
    with pytest.raises(HookInputError, match="PostToolUse, PostToolBatch, Stop"):
        read_input(hook_input(hook_event_name="SessionStart"))


# --- responding ----------------------------------------------------------------------


def test_edit_with_blocking_findings_adds_context_for_the_agent():
    out = respond(EditCheck("PostToolUse", "/repo", ("/repo/app.py",)), BLOCKING)
    assert out is not None
    hso = json.loads(out)["hookSpecificOutput"]
    assert hso["hookEventName"] == "PostToolUse"
    assert "app.py:2 [SC-CODE-001]" in hso["additionalContext"]
    assert set(json.loads(out)) == {"hookSpecificOutput"}  # never blocks


def test_batch_context_names_its_own_event():
    out = respond(EditCheck("PostToolBatch", "/repo", ("/repo/app.py",)), BLOCKING)
    assert out is not None
    assert json.loads(out)["hookSpecificOutput"]["hookEventName"] == "PostToolBatch"


def test_edit_without_blocking_findings_says_nothing():
    plan = EditCheck("PostToolUse", "/repo", ("/repo/a.py",))
    assert respond(plan, NOTE_ONLY) is None
    assert respond(plan, CLEAN) is None


def test_edit_context_lists_only_blocking_findings():
    mixed = decide([*BLOCKING.blocking, *NOTE_ONLY.non_blocking], Policy())
    out = respond(EditCheck("PostToolUse", "/repo", ("/repo/app.py",)), mixed)
    assert out is not None and "SC-CODE-002" not in out


def test_stop_with_blocking_findings_blocks_with_the_findings_as_reason():
    out = respond(StopCheck("/repo", retry=False), BLOCKING)
    assert out is not None
    doc = json.loads(out)
    assert doc["decision"] == "block"
    assert "[SC-CODE-001]" in doc["reason"]


def test_stop_already_continued_only_tells_the_user():
    out = respond(StopCheck("/repo", retry=True), BLOCKING)
    assert out is not None
    doc = json.loads(out)
    assert set(doc) == {"systemMessage"}
    assert "[SC-CODE-001]" in doc["systemMessage"]


def test_clean_stop_says_nothing():
    assert respond(StopCheck("/repo", retry=False), NOTE_ONLY) is None


def test_a_crashed_rule_is_shown_to_the_user_without_blocking():
    for plan in (EditCheck("PostToolUse", "/repo", ("/repo/a.py",)), StopCheck("/repo", False)):
        out = respond(plan, CRASHED)
        assert out is not None
        assert set(json.loads(out)) == {"systemMessage"}
        assert "results incomplete" in json.loads(out)["systemMessage"]
