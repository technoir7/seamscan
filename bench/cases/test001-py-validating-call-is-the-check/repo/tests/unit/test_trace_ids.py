import json
import uuid

import structlog

from app.logging import bind_task_trace_id, clear_task_trace_id, render_event


class _Task:
    class request:
        headers: dict[str, str] = {}


def test_trace_id_generated_when_missing() -> None:
    bind_task_trace_id(task_id="1", task=_Task())
    trace_id = structlog.contextvars.get_contextvars()["trace_id"]
    uuid.UUID(trace_id)
    clear_task_trace_id(task_id="1", task=_Task())


def test_rendered_event_is_json() -> None:
    line = render_event({"event": "started", "trace_id": "abc"})
    json.loads(line)
