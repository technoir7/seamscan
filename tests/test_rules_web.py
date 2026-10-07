"""SC-WEB-001..003 on shapes the benchmark cases don't pin down."""

from seamscan.analysis import analyze
from seamscan.model import SourceFile


def lines(rule: str, *files: tuple[str, str]) -> list[tuple[str, int]]:
    result = analyze([SourceFile(p, t) for p, t in files])
    return [(f.location.path, f.location.start_line) for f in result.findings if f.rule_id == rule]


# --- SC-WEB-003 ----------------------------------------------------------------------------------


def test_cors_in_test_files_is_ignored():
    test = (
        "server/app.test.ts",
        'import cors from "cors";\napp.use(cors({ origin: true, credentials: true }));\n',
    )
    assert lines("SC-WEB-003", test) == []


def test_non_django_settings_debug_is_not_flagged():
    settings = ("worker/settings.py", "DEBUG = True\nQUEUE_URL = 'redis://localhost'\n")
    assert lines("SC-WEB-003", settings) == []


def test_invalid_vercel_json_is_skipped():
    assert lines("SC-WEB-003", ("vercel.json", "{ not json")) == []


def test_cors_headers_on_a_browser_request_are_not_server_config():
    component = (
        "src/components/Uploader.tsx",
        "export async function upload(body: FormData) {\n"
        '  return fetch("/api/upload", { method: "POST", body, headers: {\n'
        '    "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Credentials": "true" } });\n'
        "}\n",
    )
    assert lines("SC-WEB-003", component) == []
