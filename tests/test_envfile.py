from seamscan.parse.envfile import EnvEntry, parse_env


def test_plain_assignments_with_positions():
    assert parse_env("A=1\nBB=two\n") == (EnvEntry("A", "1", 1, 3), EnvEntry("BB", "two", 2, 4))


def test_comments_blank_lines_and_non_assignments_are_skipped():
    text = "# header\n\n#COMMENTED=out\nnot an assignment\nKEY=v\n"
    assert parse_env(text) == (EnvEntry("KEY", "v", 5, 5),)


def test_export_prefix_and_spaces_around_equals():
    assert parse_env("export TOKEN=abc\n  KEY = value\n") == (
        EnvEntry("TOKEN", "abc", 1, 14),
        EnvEntry("KEY", "value", 2, 9),
    )


def test_quotes_are_removed_and_the_column_points_inside_them():
    assert parse_env("A=\"x y\"\nB='z'\n") == (EnvEntry("A", "x y", 1, 4), EnvEntry("B", "z", 2, 4))


def test_inline_comments_need_whitespace_before_the_hash():
    assert parse_env("A=1 # one\nB= # unset\nC=#not-a-comment\n") == (
        EnvEntry("A", "1", 1, 3),
        EnvEntry("B", "", 2, 4),
        EnvEntry("C", "#not-a-comment", 3, 3),
    )


def test_a_hash_inside_quotes_is_part_of_the_value():
    assert parse_env('A="p#ss # word"  # comment\n') == (EnvEntry("A", "p#ss # word", 1, 4),)


def test_quoted_empty_values():
    assert [e.value for e in parse_env("A=\"\"\nB=''\n")] == ["", ""]


def test_escaped_double_quote_does_not_close_the_value():
    assert parse_env('A="say \\"hi\\""\n')[0].value == 'say \\"hi\\"'


def test_multiline_quoted_value_keeps_its_newlines_and_start_line():
    text = 'KEY="-----BEGIN KEY-----\nabc==\n-----END KEY-----"\nNEXT=1\n'
    assert parse_env(text) == (
        EnvEntry("KEY", "-----BEGIN KEY-----\nabc==\n-----END KEY-----", 1, 6),
        EnvEntry("NEXT", "1", 4, 6),
    )


def test_unterminated_quote_keeps_the_rest_of_the_line():
    # A scanner must not lose a value to a typo, so the line is read as unquoted.
    assert parse_env('A="abc\nB=2\n') == (EnvEntry("A", '"abc', 1, 3), EnvEntry("B", "2", 2, 3))


def test_windows_line_endings():
    assert parse_env("A=1\r\nB=2\r\n") == (EnvEntry("A", "1", 1, 3), EnvEntry("B", "2", 2, 3))
