"""SC-WEB-001..003 on shapes the benchmark cases don't pin down."""

from seamscan.analysis import analyze
from seamscan.model import SourceFile


def lines(rule: str, *files: tuple[str, str]) -> list[tuple[str, int]]:
    result = analyze([SourceFile(p, t) for p, t in files])
    return [(f.location.path, f.location.start_line) for f in result.findings if f.rule_id == rule]


# --- SC-WEB-001 -----------------------------------------------------------------------------


def test_signup_and_login_routes_are_public_by_design():
    express = (
        "server/routes/auth.js",
        'const router = require("express").Router();\n'
        'router.post("/register", async (req, res) => {\n'
        "  const user = await User.create({ email: req.body.email });\n"
        "  res.json(user);\n"
        "});\n"
        'router.post("/forgot-password", async (req, res) => {\n'
        "  await PasswordReset.create({ email: req.body.email });\n"
        "  res.sendStatus(204);\n"
        "});\n",
    )
    next_route = (
        "app/api/auth/signup/route.ts",
        "export async function POST(req: Request) {\n"
        "  await prisma.user.create({ data: await req.json() });\n"
        "}\n",
    )
    action = (
        "app/(auth)/actions.ts",
        '"use server";\n'
        "export async function signUp(formData: FormData) {\n"
        "  await prisma.user.create({ data: { email: String(formData.get('email')) } });\n"
        "}\n",
    )
    fastapi = (
        "app/routers/users.py",
        "@router.post('/users/register')\n"
        "def register(body: UserIn, db: Session = Depends(get_db)):\n"
        "    db.add(User(email=body.email))\n"
        "    db.commit()\n",
    )
    assert lines("SC-WEB-001", express, next_route, action, fastapi) == []


def test_a_public_flow_word_must_be_a_whole_word():
    route = (
        "app/api/registry/route.ts",
        "export async function POST(req: Request) {\n"
        "  await prisma.registry.create({ data: await req.json() });\n"
        "}\n",
    )
    assert lines("SC-WEB-001", route) == [("app/api/registry/route.ts", 2)]


def test_msw_mock_handlers_are_not_routes():
    mock = (
        "src/mocks/handlers.ts",
        'import { http, HttpResponse } from "msw";\n'
        'import { db } from "./db";\n'
        "export const handlers = [\n"
        '  http.post("/api/todos", async ({ request }) => {\n'
        "    const todo = db.todo.create(await request.json());\n"
        "    return HttpResponse.json(todo);\n"
        "  }),\n"
        "];\n",
    )
    assert lines("SC-WEB-001", mock) == []


def test_svix_webhook_verify_counts_as_auth():
    route = (
        "app/api/webhooks/clerk/route.ts",
        'import { Webhook } from "svix";\n'
        "export async function POST(req: Request) {\n"
        "  const wh = new Webhook(process.env.CLERK_WEBHOOK_SECRET!);\n"
        "  const evt = wh.verify(await req.text(), Object.fromEntries(req.headers));\n"
        "  await prisma.user.upsert({ where: { id: evt.data.id }, create: {}, update: {} });\n"
        "}\n",
    )
    assert lines("SC-WEB-001", route) == []


def test_exported_alias_and_wrapped_handlers():
    route = (
        "app/api/items/route.ts",
        "async function create(req: Request) {\n"
        "  await prisma.item.create({ data: await req.json() });\n"
        "}\n"
        "export { create as POST };\n"
        "export const DELETE = withErrorHandling(async (req: Request) => {\n"
        "  await prisma.item.deleteMany({});\n"
        "});\n"
        "export const PUT = withAuth(async (req: Request) => {\n"
        "  await prisma.item.updateMany({ data: {} });\n"
        "});\n",
    )
    assert lines("SC-WEB-001", route) == [
        ("app/api/items/route.ts", 2),
        ("app/api/items/route.ts", 6),
    ]


def test_middleware_regex_matcher_is_not_interpreted():
    middleware = (
        "middleware.ts",
        'import { clerkMiddleware } from "@clerk/nextjs/server";\n'
        "export default clerkMiddleware(async (auth) => { await auth.protect(); });\n"
        'export const config = { matcher: ["/((?!_next|.*\\\\..*).*)", "/(api|trpc)(.*)"] };\n',
    )
    route = (
        "app/api/posts/route.ts",
        "export async function POST(req: Request) {\n"
        "  await prisma.post.create({ data: await req.json() });\n"
        "}\n",
    )
    # Documented false positive: only plain path matchers are understood.
    assert lines("SC-WEB-001", middleware, route) == [("app/api/posts/route.ts", 2)]


def test_middleware_matcher_with_route_groups_and_src_dir():
    middleware = (
        "src/middleware.ts",
        "export async function middleware(req) {\n"
        "  if (!(await getToken({ req }))) return new Response(null, { status: 401 });\n"
        "}\n"
        'export const config = { matcher: "/api/admin/:path+" };\n',
    )
    covered = (
        "src/app/(dashboard)/api/admin/users/[id]/route.ts",
        "export async function DELETE() { await prisma.user.delete({ where: { id: 1 } }); }\n",
    )
    uncovered = (
        "src/app/api/admin/route.ts",
        "export async function POST() { await prisma.setting.create({ data: {} }); }\n",
    )
    assert lines("SC-WEB-001", middleware, covered, uncovered) == [
        ("src/app/api/admin/route.ts", 1)
    ]


def test_django_view_scoped_to_request_user_is_not_flagged():
    view = (
        "notes/views.py",
        "@require_POST\n"
        "def add_note(request):\n"
        "    Note.objects.create(owner=request.user, body=request.POST['body'])\n"
        "    return redirect('notes')\n",
    )
    assert lines("SC-WEB-001", view) == []


# --- SC-WEB-002 -----------------------------------------------------------------------------


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


# --- SC-WEB-003 -----------------------------------------------------------------------------


def test_cors_in_test_files_is_ignored():
    test = (
        "server/app.test.ts",
        'import cors from "cors";\napp.use(cors({ origin: true, credentials: true }));\n',
    )
    assert lines("SC-WEB-003", test) == []


_STARLETTE_CORS = (
    "from fastapi import FastAPI\n"
    "from fastapi.middleware.cors import CORSMiddleware\n\n"
    "app = FastAPI()\n"
    'app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True)\n'
)


def test_credentialed_cors_is_harmless_when_nothing_ambient_is_sent():
    # A Bearer token travels in a header the app's own code sets; other sites can't make
    # the browser attach it, so "credentials" gives them nothing.
    bearer = ("deps.py", 'oauth2 = OAuth2PasswordBearer(tokenUrl="token")\n')
    assert lines("SC-WEB-003", ("main.py", _STARLETTE_CORS), bearer) == []


def test_credentialed_cors_is_reported_when_the_app_uses_cookies():
    login = ("auth.py", "def login(response):\n    response.set_cookie('session', 'x')\n")
    assert lines("SC-WEB-003", ("main.py", _STARLETTE_CORS), login) == [("main.py", 5)]


def test_debug_mode_does_not_depend_on_cookies():
    run = ("app.py", "from flask import Flask\napp = Flask(__name__)\napp.run(debug=True)\n")
    assert lines("SC-WEB-003", run) == [("app.py", 3)]


def test_non_django_settings_debug_is_not_flagged():
    settings = ("worker/settings.py", "DEBUG = True\nQUEUE_URL = 'redis://localhost'\n")
    assert lines("SC-WEB-003", settings) == []


def test_invalid_vercel_json_is_skipped():
    assert lines("SC-WEB-003", ("vercel.json", "{ not json")) == []


def test_admin_routes_are_never_public_flows():
    route = (
        "app/routes/admin.py",
        "@router.post('/admin/users/{user_id}/reset-password')\n"
        "def reset(user_id: int, db: Session = Depends(get_db)):\n"
        "    db.get(User, user_id).password_hash = 'x'\n"
        "    db.commit()\n",
    )
    assert lines("SC-WEB-001", route) == [("app/routes/admin.py", 4)]


def test_sdk_and_document_calls_are_not_data_writes():
    route = (
        "app/api/invoices/route.ts",
        'import twilio from "twilio";\n'
        'import { PDFDocument } from "pdf-lib";\n'
        "const client = twilio(process.env.TWILIO_SID, process.env.TWILIO_TOKEN);\n"
        "export async function POST(req: Request) {\n"
        "  const pdfDoc = await PDFDocument.create();\n"
        "  const bytes = await pdfDoc.save();\n"
        '  await client.messages.create({ body: "Invoice ready", to: "+15550100" });\n'
        "  return new Response(bytes);\n"
        "}\n",
    )
    assert lines("SC-WEB-001", route) == []


def test_mongoose_save_on_a_loaded_or_new_document_is_a_write():
    route = (
        "server/routes/profile.js",
        'const router = require("express").Router();\n'
        'router.put("/:id", async (req, res) => {\n'
        "  const user = await User.findById(req.params.id);\n"
        "  user.bio = req.body.bio;\n"
        "  await user.save();\n"
        "  res.json(user);\n"
        "});\n",
    )
    assert lines("SC-WEB-001", route) == [("server/routes/profile.js", 5)]


def test_routers_setup_and_csrf_middleware_are_not_auth():
    server = (
        "server/index.js",
        'const express = require("express");\n'
        'const passport = require("passport");\n'
        "const app = express();\n"
        "app.use(passport.initialize());\n"
        "app.use(authRoutes);\n"
        'app.post("/api/transfer", csrfProtection, async (req, res) => {\n'
        "  await Transfer.create(req.body);\n"
        "  res.sendStatus(201);\n"
        "});\n",
    )
    assert lines("SC-WEB-001", server) == [("server/index.js", 7)]


def test_wrapped_express_handler_is_analyzed():
    routes = (
        "server/routes/goals.js",
        'const asyncHandler = require("express-async-handler");\n'
        'const router = require("express").Router();\n'
        'router.post("/", asyncHandler(async (req, res) => {\n'
        "  const goal = await Goal.create({ text: req.body.text });\n"
        "  res.status(201).json(goal);\n"
        "}));\n"
        'router.delete("/:id", protect, asyncHandler(async (req, res) => {\n'
        "  await Goal.deleteOne({ _id: req.params.id });\n"
        "}));\n",
    )
    assert lines("SC-WEB-001", routes) == [("server/routes/goals.js", 4)]


def test_drf_self_request_user_scopes_the_write():
    view = (
        "api/views.py",
        "class NoteCreate(APIView):\n"
        "    def post(self, request):\n"
        "        Note.objects.create(owner=self.request.user, body=request.data['body'])\n"
        "        return Response(status=201)\n",
    )
    assert lines("SC-WEB-001", view) == []


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


def test_cors_headers_on_a_browser_request_are_not_server_config():
    component = (
        "src/components/Uploader.tsx",
        "export async function upload(body: FormData) {\n"
        '  return fetch("/api/upload", { method: "POST", body, headers: {\n'
        '    "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Credentials": "true" } });\n'
        "}\n",
    )
    assert lines("SC-WEB-003", component) == []
