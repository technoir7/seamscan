from reports.render import render_report


def test_render_is_deterministic():
    data = {"rows": [3, 1, 2], "title": "Q3"}
    assert render_report(data) == render_report(data)


def test_render_does_not_mutate_input():
    data = {"rows": [3, 1, 2], "title": "Q3"}
    assert render_report(dict(data)) == render_report(data)
