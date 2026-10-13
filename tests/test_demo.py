"""The README's GIF records `seamscan audit` on docs/demo/app; keep the two in step."""

import json
from pathlib import Path

from typer.testing import CliRunner

from seamscan.cli import app

DEMO = Path(__file__).parent.parent / "docs" / "demo" / "app"


def test_the_demo_shows_two_focus_findings_blocking_and_one_hint():
    result = CliRunner().invoke(app, ["audit", str(DEMO), "--offline", "--format", "json"])
    found = {
        (f["rule_id"], f["location"]["path"], f["blocking"])
        for f in json.loads(result.stdout)["findings"]
    }
    assert found == {
        ("SC-SEC-003", "app/api/session/route.ts", True),
        ("SC-CODE-002", "app/api/session/route.ts", False),
        ("SC-SUPA-001", "supabase/migrations/001_notes.sql", True),
    }
    assert result.exit_code == 1
