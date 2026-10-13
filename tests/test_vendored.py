"""Libraries copied into a repository: read for secrets only, like minified files."""

from bench.fake_secrets import FAKES
from seamscan.analysis import analyze
from seamscan.model import SourceFile
from seamscan.parse.javascript import text_only, vendored

SINK = "export function show(el, html) { el.innerHTML = html; }\n"
JQUERY_BANNER = (
    "/*!\n * jQuery JavaScript Library v3.7.1\n * https://jquery.com/\n *\n"
    " * Copyright OpenJS Foundation and other contributors\n"
    " * Released under the MIT license\n */\n"
)


def test_a_versioned_license_banner_marks_a_library():
    assert vendored(SourceFile("static/js/jquery.js", JQUERY_BANNER + SINK))
    select2 = (
        "/*!\n * Select2 4.0.13\n * https://select2.github.io\n *\n"
        " * Released under the MIT license\n */\n;"
    )
    assert vendored(SourceFile("static/select2.full.js", select2 + SINK))


def test_a_banner_needs_both_a_version_and_a_license():
    # An app's own header names its owner or describes the file; it doesn't version it.
    assert not vendored(SourceFile("src/app.ts", "/**\n * Copyright 2025 Acme Inc.\n */\n" + SINK))
    assert not vendored(SourceFile("src/api.ts", "/** Client for the v2.1 API. */\n" + SINK))
    # The banner has to open the file: a license comment further down is the app's.
    assert not vendored(SourceFile("src/app.ts", SINK + JQUERY_BANNER))


def test_a_vendor_directory_marks_a_library():
    for path in (
        "public/vendor/insQ.js",
        "static/vendors/chart.js",
        "web/third_party/editor.js",
        "src/staticfiles/drf-yasg/insQ.js",  # Django collectstatic output
    ):
        assert vendored(SourceFile(path, SINK)), path
    assert not vendored(SourceFile("src/vendor-utils.ts", SINK))
    assert not vendored(SourceFile("src/lib/vendors.ts", SINK))
    assert not vendored(SourceFile("vendor/client.py", "x = 1\n")), "JS and TS only"


def test_a_vendored_file_is_not_parsed_but_is_reported_and_scanned_for_secrets():
    key = FAKES["FAKE_STRIPE_LIVE"]
    text = JQUERY_BANNER + f"const k = '{key}';\n" + SINK
    result = analyze([SourceFile("server/vendor/lib.js", text)])
    assert [f.rule_id for f in result.findings] == ["SC-SEC-001"]
    assert result.not_parsed == (
        ("server/vendor/lib.js", "vendored library: checked for secrets only"),
    )
    assert text_only(SourceFile("app/x.min.js", "a")) == "minified"
    assert text_only(SourceFile("src/app.ts", SINK)) is None
