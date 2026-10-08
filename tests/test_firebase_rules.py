import pytest

from seamscan.model import Location, SourceFile
from seamscan.parse.firebase_rules import (
    DatabaseRule,
    RulesSyntaxError,
    disjuncts,
    looks_like_database_rules,
    looks_like_security_rules,
    normalize,
    parse_database_rules,
    parse_rules,
)


def rules(text: str):
    return parse_rules(SourceFile("firestore.rules", text))


TEST_MODE = """rules_version = '2';

service cloud.firestore {
  match /databases/{database}/documents {
    // open until the date
    match /{document=**} {
      allow read, write: if request.time < timestamp.date(2026, 11, 7);
    }
  }
}
"""


def test_test_mode_rules():
    parsed = rules(TEST_MODE)
    assert parsed.version == "2"
    (allow,) = parsed.allows
    assert allow.service == "cloud.firestore"
    assert allow.path == ("databases", "{database}", "documents", "{document=**}")
    assert allow.ops == ("read", "write")
    assert allow.condition == "request.time < timestamp.date(2026, 11, 7)"
    assert allow.normalized == "request.time<timestamp.date(2026,11,7)"
    assert allow.location == Location("firestore.rules", 7, 7, 7, 72)
    assert allow.text == "allow read, write: if request.time < timestamp.date(2026, 11, 7);"


def test_bare_allow_has_no_condition_and_normalizes_to_true():
    (allow,) = rules("service cloud.firestore { match /a/{b} { allow read; } }").allows
    assert allow.condition is None
    assert allow.normalized == "true"
    assert allow.text == "allow read;"


def test_storage_service_and_nested_paths_concatenate():
    text = """service firebase.storage {
  match /b/{bucket}/o {
    match /users/{userId} {
      match /{allPaths=**} {
        allow get, list: if request.auth.uid == userId;
      }
    }
  }
}"""
    (allow,) = rules(text).allows
    assert allow.service == "firebase.storage"
    assert allow.path == ("b", "{bucket}", "o", "users", "{userId}", "{allPaths=**}")
    assert allow.ops == ("get", "list")


def test_path_block_brace_without_space():
    (allow,) = rules(
        "service cloud.firestore {match /{document=**}{allow write: if false;}}"
    ).allows
    assert allow.path == ("{document=**}",)
    assert allow.normalized == "false"


def test_multiline_condition_keeps_its_text_and_span():
    text = """service firebase.storage {
  match /b/{bucket}/o/{name} {
    allow write: if request.auth != null
                 && request.resource.size < 5 * 1024 * 1024; // 5 MB
  }
}"""
    (allow,) = rules(text).allows
    assert allow.normalized == "request.auth!=null&&request.resource.size<5*1024*1024"
    assert (allow.location.start_line, allow.location.end_line) == (3, 4)


def test_comments_and_strings_do_not_confuse_the_parser():
    text = """service cloud.firestore {
  match /databases/{database}/documents {
    // allow read, write: if true;
    /* match /{document=**} { allow read, write: if true; } */
    match /notes/{id} {
      allow read: if resource.data.label == "a;b}" && 'x // y' != '';
    }
  }
}"""
    (allow,) = rules(text).allows
    assert allow.normalized == "resource.data.label==\"a;b}\"&&'x // y'!=''"


def test_functions_are_recorded_with_their_scope_and_single_return():
    text = """service cloud.firestore {
  match /databases/{database}/documents {
    function isSignedIn() {
      return request.auth != null;
    }
    match /users/{userId} {
      function isOwner(uid) { return isSignedIn() && request.auth.uid == uid; }
      function complex() { let a = 1; return a == 1; }
      allow read: if isOwner(userId);
    }
  }
}"""
    parsed = rules(text)
    assert [(f.name, f.params, f.returns, f.scope) for f in parsed.functions] == [
        ("isSignedIn", (), "request.auth!=null", ("databases", "{database}", "documents")),
        (
            "isOwner",
            ("uid",),
            "isSignedIn()&&request.auth.uid==uid",
            ("databases", "{database}", "documents", "users", "{userId}"),
        ),
        ("complex", (), None, ("databases", "{database}", "documents", "users", "{userId}")),
    ]
    assert [a.normalized for a in parsed.allows] == ["isOwner(userId)"]


def test_maps_and_get_paths_inside_conditions():
    text = """service cloud.firestore {
  match /databases/{database}/documents/projects/{p} {
    allow read: if get(/databases/$(database)/documents/projects/$(p))
      .data.members[request.auth.uid] == true;
    allow update: if request.resource.data.diff(resource.data)
      .affectedKeys().hasOnly({'a': 1}.keys());
  }
}"""
    allows = rules(text).allows
    assert len(allows) == 2
    assert allows[1].ops == ("update",)


def test_missing_semicolon_before_block_end_or_next_statement():
    text = """service cloud.firestore {
  match /a/{b} {
    allow read: if true
    allow write: if false
  }
}"""
    assert [(a.ops, a.normalized) for a in rules(text).allows] == [
        (("read",), "true"),
        (("write",), "false"),
    ]


@pytest.mark.parametrize(
    ("text", "line"),
    [
        ("service cloud.firestore {\n  match /a {\n    allow read: if true;\n", 2),
        ("service cloud.firestore {\n  allow fly: if true;\n}", 2),
        ("service cloud.firestore {\n  match {\n  }\n}", 2),
        ("service cloud.firestore {\n  permit read;\n}", 2),
        ("/* never closed\nservice cloud.firestore {}", 1),
    ],
)
def test_syntax_errors_name_a_line(text: str, line: int):
    with pytest.raises(RulesSyntaxError) as err:
        rules(text)
    assert err.value.line == line


def test_normalize_and_disjuncts():
    assert normalize("( true )") == "true"
    assert normalize("x in ['a', 'b']") == "x in['a','b']"
    assert normalize("data.v is string") == "data.v is string"
    assert normalize("(a) && (b)") == "(a)&&(b)"
    assert disjuncts("true||(request.auth!=null&&x)") == ("true", "request.auth!=null&&x")
    assert disjuncts("f(a||b)") == ("f(a||b)",)


def test_security_rules_sniffing():
    assert looks_like_security_rules("firestore.rules", TEST_MODE)
    assert looks_like_security_rules("rules/prod.rules", "service firebase.storage {}")
    assert not looks_like_security_rules("99-usb.rules", 'SUBSYSTEM=="tty", MODE="0666"')
    assert not looks_like_security_rules("firestore.txt", TEST_MODE)


def db(text: str):
    return parse_database_rules(SourceFile("database.rules.json", text))


def test_database_rules_at_any_depth_with_positions():
    text = """{
  "rules": {
    ".read": true,
    "users": {
      "$uid": {
        ".write": "auth != null && auth.uid === $uid",
        ".validate": "newData.hasChildren(['name'])"
      }
    }
  }
}"""
    assert db(text) == (
        DatabaseRule((), ".read", True, "true", Location("database.rules.json", 3, 5, 3, 18)),
        DatabaseRule(
            ("users", "$uid"),
            ".write",
            "auth != null && auth.uid === $uid",
            "auth!=null&&auth.uid===$uid",
            Location("database.rules.json", 6, 9, 6, 54),
        ),
    )


def test_database_rules_accept_comments_and_trailing_commas():
    # The Firebase console's own test-mode template has both.
    text = '{\n  "rules": {\n    ".read": "now < 1767225600000",  // 2026-1-1\n  },\n}\n'
    (rule,) = db(text) or ()
    assert rule.normalized == "now<1767225600000"


def test_json_without_a_rules_object_is_not_database_rules():
    assert db('{"viewer": {".read": true}}') is None
    assert db('{"rules": "strict"}') is None


@pytest.mark.parametrize(
    ("text", "line"),
    [
        ('{\n  "rules": {\n    ".read": 1\n  }\n}', 3),
        ('{\n  "rules": {\n    ".read": true\n', 4),
        ('{\n  "rules": {".read" true}\n}', 2),
    ],
)
def test_database_rules_errors(text: str, line: int):
    with pytest.raises(RulesSyntaxError) as err:
        db(text)
    assert err.value.line == line


def test_database_rules_sniffing():
    assert looks_like_database_rules("database.rules.json", '{"rules": {".read": false}}')
    assert not looks_like_database_rules("package.json", '{"name": "x"}')
    assert not looks_like_database_rules("database.rules.txt", '{"rules": {".read": false}}')
