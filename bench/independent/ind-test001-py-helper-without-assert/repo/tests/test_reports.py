import datetime as dt

from reports.monthly import build_report


def _make_report(month):
    return build_report(dt.date(2026, month, 1), include_refunds=True)


def test_monthly_report_totals_match_ledger():
    report = _make_report(3)
    report.render()


def test_monthly_report_has_title():
    assert _make_report(4).title == "April 2026"
