"""SC-SEC-002: secrets reachable from the browser, and how it divides work with SEC-001/004."""

from bench.fake_secrets import FAKES
from seamscan.analysis import analyze
from seamscan.model import Finding, Location, Severity, SourceFile
from seamscan.rules.base import Rule
from seamscan.rules.secrets import CLIENT_EXPOSURE, ENV_FILE_COMMITTED, PROVIDER_SECRET, RULES

RULE: dict[str, Rule] = {r.meta.id: r for r in RULES}
NEXT_PKG = '{"dependencies": {"next": "15.0.3", "react": "19.0.0"}}'
VITE_PKG = '{"dependencies": {"react": "18.3.1"}, "devDependencies": {"vite": "5.4.10"}}'


def run(rule_id: str, files: dict[str, str]) -> tuple[Finding, ...]:
    sources = [SourceFile(path, text) for path, text in files.items()]
    return analyze(sources, rules=[RULE[rule_id]]).findings


def exposure(files: dict[str, str]) -> tuple[Finding, ...]:
    return run(CLIENT_EXPOSURE.id, files)


def where(findings: tuple[Finding, ...]) -> list[tuple[str, int]]:
    return [(f.location.path, f.location.start_line) for f in findings]


# ---------------------------------------------------------------- literals in client files


def test_literal_in_client_file_is_sec002_and_not_sec001():
    key = FAKES["FAKE_STRIPE_LIVE"]
    files = {
        "package.json": NEXT_PKG,
        "components/Pay.tsx": f'"use client";\nnew Stripe("{key}");\n',
    }
    (f,) = exposure(files)
    assert f.severity is Severity.CRITICAL
    assert "browser" in f.message
    assert where((f,)) == [("components/Pay.tsx", 2)]
    assert not run(PROVIDER_SECRET.id, files)


def test_literal_in_server_or_unknown_file_stays_sec001():
    key = FAKES["FAKE_STRIPE_LIVE"]
    files = {
        "package.json": NEXT_PKG,
        "app/api/pay/route.ts": f'new Stripe("{key}");\n',
        "scripts/seed.mjs": f'new Stripe("{key}");\n',
    }
    assert not exposure(files)
    assert len(run(PROVIDER_SECRET.id, files)) == 2


def test_test_mode_key_in_client_file_is_low():
    key = FAKES["FAKE_STRIPE_TEST"]
    (f,) = exposure({"package.json": VITE_PKG, "src/pay.ts": f'export const k = "{key}";\n'})
    assert f.severity is Severity.LOW


def test_publishable_and_placeholder_literals_in_client_files_are_fine():
    src = (
        f'loadStripe("{FAKES["FAKE_STRIPE_PK_LIVE"]}");\n'
        f'createClient(url, "{FAKES["FAKE_SUPABASE_PUBLISHABLE"]}");\n'
        f'createClient(url, "{FAKES["FAKE_SUPABASE_ANON_JWT"]}");\n'
        f'const hint = "{FAKES["FAKE_OPENAI_YOUR_KEY"]}";\n'
    )
    assert not exposure({"package.json": VITE_PKG, "src/lib/clients.ts": src})


# ---------------------------------------------------------------- .env definitions


def test_secret_value_under_public_name_is_reported_at_the_value_with_client_reads_related():
    jwt = FAKES["FAKE_SUPABASE_SERVICE_JWT"]
    env = f"NEXT_PUBLIC_SUPABASE_URL=https://x.supabase.co\nNEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY={jwt}\n"
    client = '"use client";\nconst k = process.env.NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY;\n'
    server = "const k = process.env.NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY;\n"
    files = {
        "package.json": NEXT_PKG,
        ".env.local": env,
        "components/Admin.tsx": client,
        "app/api/admin/route.ts": server,
    }
    (f,) = exposure(files)
    start = len("NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY=") + 1
    assert f.location == Location(".env.local", 2, start, 2, start + len(jwt))
    assert f.severity is Severity.CRITICAL
    # Only the browser read is related: the route handler runs on the server.
    assert [(r.path, r.start_line) for r in f.related] == [("components/Admin.tsx", 2)]
    assert jwt not in f.message + f.evidence
    # One key, one finding: SC-SEC-001 leaves bundled-public variables to SC-SEC-002.
    assert not run(PROVIDER_SECRET.id, files)


def test_the_value_decides_over_the_name():
    env = (
        f"VITE_SUPABASE_ANON_KEY={FAKES['FAKE_SUPABASE_SERVICE_JWT']}\n"
        f"NEXT_PUBLIC_STRIPE_SECRET_KEY={FAKES['FAKE_STRIPE_PK_LIVE']}\n"
        f"VITE_FIREBASE_API_KEY={FAKES['FAKE_OPENAI_PROJ']}\n"
    )
    assert where(exposure({".env": env})) == [(".env", 1), (".env", 3)]


def test_secret_names_without_a_provider_shape():
    env = (
        "NEXT_PUBLIC_ADMIN_SECRET=quizly-admin-letmein\n"
        "VITE_SUPABASE_SERVICE_ROLE_KEY=abc.def.ghi\n"
        "VITE_FIREBASE_PRIVATE_KEY=-----BEGIN-PRIVATE-KEY-----\n"
        "VITE_WEATHER_API_KEY=3f9a2c7e1b4d\n"
        "NEXT_PUBLIC_ALGOLIA_ADMIN_KEY=9d8e7f6a5b4c\n"
    )
    found = exposure({".env": env})
    assert [(f.location.start_line, f.severity) for f in found] == [
        (1, Severity.CRITICAL),
        (2, Severity.CRITICAL),
        (3, Severity.CRITICAL),
        (4, Severity.HIGH),  # only the last-word rule says secret
        (5, Severity.CRITICAL),
    ]
    assert "quizly-admin-letmein" not in found[0].message + found[0].evidence


def test_public_by_design_names_and_settings_are_not_reported():
    env = (
        "NEXT_PUBLIC_SUPABASE_ANON_KEY=anon\n"
        "VITE_SUPABASE_PUBLISHABLE_KEY=pub\n"
        "VITE_VAPID_PUBLIC_KEY=BEl62iUYgU\n"
        "VITE_MAPBOX_PUBLIC_TOKEN=pk.abc\n"
        "VITE_FIREBASE_API_KEY=AIzaSyB7\n"
        "NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=AIzaSyC2\n"
        "NEXT_PUBLIC_POSTHOG_KEY=phc_abc\n"
        "REACT_APP_SEGMENT_WRITE_KEY=wk_abc\n"
        "NEXT_PUBLIC_ALGOLIA_SEARCH_API_KEY=6be0576f\n"
        "NEXT_PUBLIC_TURNSTILE_SITE_KEY=0x4AAA\n"
        "EXPO_PUBLIC_REVENUECAT_KEY=appl_abc\n"
        "NEXT_PUBLIC_MAPBOX_TOKEN=pk.abc\n"
        "NEXT_PUBLIC_ADMIN_EMAIL=ops@acme.dev\n"
        "NEXT_PUBLIC_API_URL=https://api.acme.dev\n"
    )
    assert not exposure({".env": env})


def test_public_by_design_names_still_fire_on_a_secret_word():
    env = "NEXT_PUBLIC_POSTHOG_PERSONAL_API_KEY=phx_abc\nVITE_FIREBASE_ADMIN_SECRET=s3cr3t\n"
    assert where(exposure({".env": env})) == [(".env", 1), (".env", 2)]


def test_placeholders_and_unprefixed_names_are_not_definitions_to_report():
    env = (
        "NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY=your-service-role-key\n"
        f"VITE_OPENAI_API_KEY={FAKES['FAKE_OPENAI_YOUR_KEY']}\n"
        "VITE_STRIPE_SECRET_KEY=\n"
        f"SUPABASE_SERVICE_ROLE_KEY={FAKES['FAKE_SUPABASE_SERVICE_JWT']}\n"
    )
    assert not exposure({".env.example": env})


# ---------------------------------------------------------------- reads with no real definition


def test_read_in_client_file_is_reported_when_no_env_defines_it():
    src = (
        "const a = import.meta.env.VITE_OPENAI_API_KEY;\n"
        'const b = import.meta.env["VITE_STRIPE_SECRET_KEY"];\n'
        "const c = import.meta.env.VITE_SUPABASE_ANON_KEY;\n"
        "const d = import.meta.env.OPENAI_API_KEY;\n"  # unprefixed: undefined in the browser
    )
    found = exposure({"package.json": VITE_PKG, "src/lib/ai.ts": src})
    assert [(f.location.start_line, f.severity) for f in found] == [
        (1, Severity.HIGH),
        (2, Severity.CRITICAL),
    ]
    assert found[0].evidence == "import.meta.env.VITE_OPENAI_API_KEY"


def test_read_is_reported_once_per_file_and_only_in_client_files():
    read = "process.env.NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY"
    files = {
        "package.json": NEXT_PKG,
        "components/A.tsx": f'"use client";\nconst a = {read};\nconst b = {read};\n',
        "app/api/x/route.ts": f"const a = {read};\n",
        "lib/admin.ts": f"const a = {read};\n",  # unknown role: may never reach a browser
        "components/A.test.tsx": f'"use client";\nconst a = {read};\n',
    }
    assert where(exposure(files)) == [("components/A.tsx", 2)]


def test_a_placeholder_definition_does_not_hide_the_read_but_a_real_one_does():
    src = '"use client";\nconst k = process.env.NEXT_PUBLIC_STRIPE_SECRET_KEY;\n'
    files = {"package.json": NEXT_PKG, "components/Pay.tsx": src}
    placeholder = {**files, ".env.example": "NEXT_PUBLIC_STRIPE_SECRET_KEY=changeme\n"}
    assert where(exposure(placeholder)) == [("components/Pay.tsx", 2)]
    real = {**files, ".env": "NEXT_PUBLIC_STRIPE_SECRET_KEY=s3cr3t-value\n"}
    (f,) = exposure(real)
    assert f.location.path == ".env"
    assert [(r.path, r.start_line) for r in f.related] == [("components/Pay.tsx", 2)]


# ---------------------------------------------------------------- SC-SEC-004 alignment


def test_committed_env_with_only_public_by_design_keys_is_not_sec004():
    env = f"VITE_FIREBASE_API_KEY={FAKES['FAKE_FIREBASE_WEB_API_KEY']}\nVITE_POSTHOG_KEY=phc_x\n"
    assert not run(ENV_FILE_COMMITTED.id, {".env": env})
    env = f"NEXT_PUBLIC_STRIPE_KEY={FAKES['FAKE_STRIPE_PK_LIVE']}\n"
    assert not run(ENV_FILE_COMMITTED.id, {".env": env})


def test_committed_env_with_a_secret_in_a_public_variable_is_still_sec004():
    env = f"NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY={FAKES['FAKE_SUPABASE_SERVICE_JWT']}\n"
    (f,) = run(ENV_FILE_COMMITTED.id, {".env.local": env})
    assert f.location.start_line == 1
