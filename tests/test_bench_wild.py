import json
import tomllib
from pathlib import Path

from bench.wild import Study, draw_sample, per_kloc, precision, sample


def _findings(n: int) -> list[dict[str, object]]:
    return [
        {"repo": f"r{i % 3}", "rule": "SC-X", "path": "a.py", "line": i, "fingerprint": f"{i:04x}"}
        for i in range(n)
    ]


def test_the_sample_is_the_same_for_the_same_seed_and_any_input_order():
    findings = _findings(300)
    first = draw_sample(findings, 100, seed=7)
    again = draw_sample(list(reversed(findings)), 100, seed=7)
    assert first == again
    assert len(first) == 100


def test_a_small_population_is_sampled_whole():
    assert len(draw_sample(_findings(40), 100, seed=7)) == 40


def test_findings_per_thousand_lines():
    assert per_kloc(3, 1500) == 2.0
    assert per_kloc(0, 0) == 0.0


def test_precision_leaves_unclear_verdicts_out_of_the_ratio():
    result = precision(["true", "true", "true", "false", "unclear"])
    assert result["precision"] == 0.75
    assert result["unclear"] == 1
    assert result["sampled"] == 5


def test_the_triage_sample_keeps_any_message_text_readable_as_toml(tmp_path: Path):
    # JSON's ASCII escapes write an emoji as a surrogate pair, which TOML rejects.
    message = "`_t('\U0001f680 Start')` is \"raw\"\n\tHTML"
    finding = {**_findings(1)[0], "message": message}
    study = Study(
        tmp_path / "r.toml", tmp_path / "d.json", tmp_path / "t.toml", tmp_path / "c.json"
    )
    study.detail.write_text(json.dumps([finding]))
    sample(study, 10, seed=7)
    (entry,) = tomllib.loads(study.triage.read_text())["finding"]
    assert entry["message"] == message
