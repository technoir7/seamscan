from seamscan.model import WHOLE_FILE, ChangeSet
from seamscan.parse.diff import parse_unified_diff

DIFF = """\
diff --git a/app.py b/app.py
index 1111111..2222222 100644
--- a/app.py
+++ b/app.py
@@ -3,0 +4,2 @@ def f():
+    a = 1
+    b = 2
@@ -10 +12 @@ def g():
-    old
+    new
@@ -20,3 +23,0 @@ def h():
-    gone
-    gone
-    gone
diff --git a/old_name.py b/new_name.py
similarity index 90%
rename from old_name.py
rename to new_name.py
--- a/old_name.py
+++ b/new_name.py
@@ -1 +1 @@
-x = 1
+x = 2
diff --git a/removed.py b/removed.py
deleted file mode 100644
--- a/removed.py
+++ /dev/null
@@ -1 +0,0 @@
-gone = True
"""


def test_added_line_ranges_per_file():
    change = parse_unified_diff(DIFF)
    assert change.added["app.py"] == ((4, 5), (12, 12))


def test_renamed_file_is_tracked_under_new_path():
    change = parse_unified_diff(DIFF)
    assert change.added["new_name.py"] == ((1, 1),)
    assert "old_name.py" not in change.added


def test_deleted_file_has_no_added_lines():
    assert "removed.py" not in parse_unified_diff(DIFF).added


def test_touches_checks_overlap():
    change = ChangeSet(added={"app.py": ((4, 5),), "new.py": (WHOLE_FILE,)})
    assert change.touches("app.py", 5, 5)
    assert change.touches("app.py", 1, 4)
    assert not change.touches("app.py", 6, 9)
    assert change.touches("new.py", 9000, 9000)
    assert not change.touches("other.py", 1, 1)
