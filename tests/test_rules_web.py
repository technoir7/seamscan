"""SC-WEB-001..003 on shapes the benchmark cases don't pin down."""

from seamscan.analysis import analyze
from seamscan.model import SourceFile


def lines(rule: str, *files: tuple[str, str]) -> list[tuple[str, int]]:
    result = analyze([SourceFile(p, t) for p, t in files])
    return [(f.location.path, f.location.start_line) for f in result.findings if f.rule_id == rule]


# --- SC-WEB-002 ----------------------------------------------------------------------------------


def test_fixed_host_without_a_path_separator_is_still_ssrf():
    # "https://api.example.com" + "@evil.test" sends the request to evil.test.
    route = (
        "app/api/proxy/route.ts",
        "export async function GET(req: Request) {\n"
        "  const path = new URL(req.url).searchParams.get('path');\n"
        "  return fetch(`https://api.example.com${path}`);\n"
        "}\n",
    )
    assert lines("SC-WEB-002", route) == [("app/api/proxy/route.ts", 3)]


def test_new_url_with_user_first_argument_overrides_the_base():
    route = (
        "server/proxy.js",
        'const express = require("express");\n'
        "const app = express();\n"
        'app.get("/p", async (req, res) => {\n'
        '  const r = await fetch(new URL(req.query.path, "https://api.example.com"));\n'
        "  res.send(await r.text());\n"
        "});\n",
    )
    assert lines("SC-WEB-002", route) == [("server/proxy.js", 4)]


def test_axios_config_object_url():
    route = (
        "pages/api/fetch.ts",
        'import axios from "axios";\n'
        "export default async function handler(req, res) {\n"
        '  const r = await axios({ method: "get", url: req.body.target });\n'
        "  res.json(r.data);\n"
        "}\n",
    )
    assert lines("SC-WEB-002", route) == [("pages/api/fetch.ts", 3)]


def test_helper_parameter_is_not_request_input():
    helper = (
        "lib/http.ts",
        "export async function getJson(url: string) {\n"
        "  const r = await fetch(url);\n"
        "  return r.json();\n"
        "}\n",
    )
    py_helper = (
        "app/clients.py",
        "import requests\n\ndef get_json(url):\n    return requests.get(url, timeout=5).json()\n",
    )
    assert lines("SC-WEB-002", helper, py_helper) == []


def test_python_unbound_client_call():
    view = (
        "app/main.py",
        "import httpx\n"
        "@app.get('/fetch')\n"
        "async def fetch(url: str):\n"
        "    return (await httpx.AsyncClient().get(url)).text\n",
    )
    assert lines("SC-WEB-002", view) == [("app/main.py", 4)]


def test_is_valid_url_is_a_format_check_not_an_allowlist():
    view = (
        "app.py",
        "import requests\n"
        "from flask import request\n"
        "@app.post('/fetch')\n"
        "def fetch():\n"
        "    url = request.json['url']\n"
        "    if not is_valid_url(url):\n"
        "        return 'bad', 400\n"
        "    return requests.get(url, timeout=5).text\n",
    )
    assert lines("SC-WEB-002", view) == [("app.py", 8)]


def test_helper_named_query_or_params_is_not_request_input():
    helper = (
        "app/lib/search.ts",
        "export async function search(query: string, params: string) {\n"
        "  await fetch(params);\n"
        "  return fetch(query);\n"
        "}\n",
    )
    page = (
        "app/preview/page.tsx",
        "export default async function Page({ searchParams }: { searchParams: { u: string } }) {\n"
        "  const html = await (await fetch(searchParams.u)).text();\n"
        "  return <pre>{html}</pre>;\n"
        "}\n",
    )
    assert lines("SC-WEB-002", helper, page) == [("app/preview/page.tsx", 2)]


def test_django_class_view_self_request():
    view = (
        "feeds/views.py",
        "import requests\n"
        "class FeedView(View):\n"
        "    def get(self, request):\n"
        "        return HttpResponse(requests.get(self.request.GET['url'], timeout=5).text)\n",
    )
    assert lines("SC-WEB-002", view) == [("feeds/views.py", 4)]


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
