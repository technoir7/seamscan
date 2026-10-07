from config.loader import load_config


def test_load_config_with_empty_file_does_not_raise(tmp_path):
    path = tmp_path / "settings.toml"
    path.write_text("")
    load_config(path)


def test_example_config_loads():
    """The shipped example config must load without raising."""
    load_config("config/example.toml")
