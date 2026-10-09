"""Minified build output: not parsed as code, still scanned for secrets, never silent."""

from pathlib import Path

from typer.testing import CliRunner

from bench.fake_secrets import FAKES
from seamscan.analysis import analyze
from seamscan.cli import app
from seamscan.model import SourceFile
from seamscan.parse.javascript import minified

BUNDLE = "/*! lib */\n!function(){" + "var a=document.body;" * 200 + "a.innerHTML=x.html}();\n"


def test_long_lines_on_average_mark_build_output():
    assert minified(SourceFile("static/vendor/tour.iife.js", BUNDLE))
    assert minified(SourceFile("lib/x.min.js", "var a=1;\n"))
    # A short one-line constant is source, however long its line.
    assert not minified(SourceFile("lib/constants.ts", "export const A = '" + "x" * 600 + "';"))
    assert not minified(SourceFile("src/app.ts", "const a = 1;\n" * 400))
    assert not minified(SourceFile("data.json", BUNDLE))


def test_a_minified_file_is_not_parsed_but_is_reported_and_scanned_for_secrets():
    text = BUNDLE.replace("var a=", f"var k='{FAKES['FAKE_STRIPE_LIVE']}',a=", 1)
    result = analyze([SourceFile("public/assets/index.js", text)])
    assert [f.rule_id for f in result.findings] == ["SC-SEC-001"]
    assert result.not_parsed == (("public/assets/index.js", "minified: checked for secrets only"),)


def test_stats_list_minified_files_with_the_skipped_ones(tmp_path: Path):
    (tmp_path / "tour.iife.js").write_text(BUNDLE)
    result = CliRunner().invoke(app, ["audit", str(tmp_path), "--offline", "--stats"])
    assert "tour.iife.js: minified: checked for secrets only" in result.stderr
