from app.db import connect


def test_connection():
    """Startup self-check run by the health endpoint."""
    connect().ping()
