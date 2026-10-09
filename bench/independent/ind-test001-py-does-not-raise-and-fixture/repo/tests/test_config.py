import pytest

from app.config import load_config
from app.models import User


@pytest.fixture
def test_user():
    return User(id=1, name="ada")


def test_load_config_with_empty_file_does_not_raise(tmp_path):
    (tmp_path / "empty.toml").write_text("")
    load_config(tmp_path / "empty.toml")


def test_load_config_defaults(tmp_path):
    """Must load without raising when keys are missing."""
    (tmp_path / "c.toml").write_text("[app]\n")
    load_config(tmp_path / "c.toml")


def test_smoke_import_all_plugins():
    import app.plugins  # noqa: F401
    app.plugins.discover()
