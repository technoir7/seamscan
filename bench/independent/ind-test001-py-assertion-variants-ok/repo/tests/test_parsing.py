import warnings
from unittest import mock

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from app.parsing import legacy_parse, load_frame, notify, parse


def test_rejects_empty():
    with pytest.raises(ValueError):
        parse("")


def test_warns_on_legacy_format():
    with pytest.warns(DeprecationWarning):
        legacy_parse("a;b")


def test_notify_calls_hook():
    hook = mock.Mock()
    notify("done", hook=hook)
    hook.assert_called_once_with("done")


def test_frame_roundtrip(tmp_path):
    df = pd.DataFrame({"a": [1, 2]})
    df.to_csv(tmp_path / "x.csv", index=False)
    assert_frame_equal(load_frame(tmp_path / "x.csv"), df)


def test_check_helper_name():
    check_schema(parse("a=1"))


def check_schema(parsed):
    assert set(parsed) == {"a"}


def test_manual_fail():
    try:
        parse("a=1")
    except Exception as exc:
        pytest.fail(f"unexpected: {exc}")
