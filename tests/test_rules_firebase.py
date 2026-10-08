"""SC-FIRE-001 behavior the benchmark can't see: severity per finding, messages, failures."""

from seamscan.analysis import analyze
from seamscan.model import Finding, Severity, SourceFile
from seamscan.rules.firebase import RULES


def run(files: dict[str, str]) -> tuple[Finding, ...]:
    return analyze([SourceFile(p, t) for p, t in files.items()], rules=RULES).findings


def firestore(body: str) -> dict[str, str]:
    return {
        "firestore.rules": "rules_version = '2';\nservice cloud.firestore {\n"
        "  match /databases/{database}/documents {\n" + body + "\n  }\n}\n"
    }


def severities(files: dict[str, str]) -> list[tuple[int, Severity]]:
    return [(f.location.start_line, f.severity) for f in run(files)]


def test_open_catch_all_is_critical_and_names_the_scope():
    (f,) = run(firestore("    match /{document=**} { allow read, write: if true; }"))
    assert f.severity == Severity.CRITICAL
    assert f.rule_id == "SC-FIRE-001"
    assert "every document in Firestore" in f.message
    assert f.evidence == "allow read, write: if true;"


def test_test_mode_message_gives_the_date_and_says_it_will_break():
    (f,) = run(
        firestore(
            "    match /{document=**} {\n"
            "      allow read, write: if request.time < timestamp.date(2026, 1, 7);\n"
            "    }"
        )
    )
    assert f.severity == Severity.CRITICAL
    assert "2026-01-07" in f.message
    assert "denied" in f.message


def test_signed_in_only_on_catch_all_is_high_and_ignored_on_a_named_collection():
    body = (
        "    match /{document=**} { allow read: if request.auth != null; }\n"
        "    match /posts/{id} { allow read, write: if request.auth != null; }"
    )
    assert severities(firestore(body)) == [(4, Severity.HIGH)]


def test_public_read_of_a_named_collection_is_low_but_public_write_is_critical():
    body = (
        "    match /posts/{id} {\n"
        "      allow read: if true;\n"
        "      allow create: if true;\n"
        "    }\n"
        "    match /posts/{id}/comments/{c} { allow list: if (true); }"
    )
    assert severities(firestore(body)) == [
        (5, Severity.LOW),
        (6, Severity.CRITICAL),
        (8, Severity.LOW),
    ]


def test_a_root_level_variable_collection_counts_as_catch_all():
    body = "    match /{collection}/{doc} { allow read: if true; }"
    assert severities(firestore(body)) == [(4, Severity.CRITICAL)]


def test_a_collection_group_match_names_its_collection():
    body = "    match /{path=**}/posts/{postId} { allow read: if true; }"
    assert severities(firestore(body)) == [(4, Severity.LOW)]


def test_true_as_one_branch_of_an_or_is_still_open():
    body = "    match /{d=**} { allow read: if request.auth.uid == 'x' || true; }"
    assert severities(firestore(body)) == [(4, Severity.CRITICAL)]


def test_zero_argument_helpers_are_inlined_through_chains_but_not_with_arguments():
    body = (
        "    function signedIn() { return request.auth != null; }\n"
        "    function canRead() { return signedIn(); }\n"
        "    function owns(u) { return request.auth.uid == u; }\n"
        "    match /{d=**} { allow read: if canRead(); allow write: if owns('a'); }"
    )
    assert severities(firestore(body)) == [(7, Severity.HIGH)]


def test_helper_declared_in_a_sibling_match_is_not_visible():
    body = (
        "    match /a/{x} { function open() { return true; } }\n"
        "    match /{d=**} { allow read: if open(); }"
    )
    assert run(firestore(body)) == ()


def test_owner_checks_and_false_are_not_flagged():
    body = (
        "    match /users/{userId} { allow read, write: if request.auth.uid == userId; }\n"
        "    match /{document=**} { allow read, write: if false; }\n"
        "    match /p/{id} { allow read: if resource.data.owner == request.auth.uid; }"
    )
    assert run(firestore(body)) == ()


def test_storage_catch_all_is_named_as_storage():
    text = (
        "service firebase.storage {\n  match /b/{bucket}/o {\n"
        "    match /{allPaths=**} { allow read; }\n  }\n}\n"
    )
    (f,) = run({"storage.rules": text})
    assert f.severity == Severity.CRITICAL
    assert "every file in Cloud Storage" in f.message


def test_realtime_database_severities():
    text = """{
  "rules": {
    ".read": "auth != null",
    "$other": { ".write": "now < 1767225600000" },
    "posts": { ".read": true, ".write": "auth !== null" },
    "users": { "$uid": { ".write": true } }
  }
}
"""
    found = run({"database.rules.json": text})
    assert [(f.location.start_line, f.location.start_col, f.severity) for f in found] == [
        (3, 5, Severity.HIGH),
        (4, 17, Severity.CRITICAL),
        (5, 16, Severity.LOW),
        (6, 26, Severity.CRITICAL),
    ]
    assert "2026-01-01" in found[1].message


def test_unparseable_rules_are_reported_not_skipped():
    (f,) = run({"firestore.rules": "service cloud.firestore {\n  match /a/{b} {\n"})
    assert f.rule_id == "SC-META-002"
    assert f.location.start_line == 2


def test_unparseable_database_rules_are_reported():
    (f,) = run({"database.rules.json": '{\n  "rules": {\n    ".read": tru\n  }\n}\n'})
    assert f.rule_id == "SC-META-002"


def test_files_that_only_share_the_extension_are_ignored():
    files = {
        "99-usb.rules": 'SUBSYSTEM=="tty", MODE="0666"\n',
        "src/perm.json": '{"viewer": {".read": true}}\n',
        "firestore.rules.md": "allow read, write: if true;\n",
    }
    assert run(files) == ()


def test_realtime_database_true_as_a_string_and_owner_hint_in_its_syntax():
    text = '{"rules": {".write": "true", ".read": "auth.uid != null"}}'
    found = run({"database.rules.json": text})
    assert [f.severity for f in found] == [Severity.CRITICAL, Severity.HIGH]
    assert "`auth.uid === $uid`" in found[1].message
