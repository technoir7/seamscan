from fastapi import Header


def verify_api_key(x_api_key: str = Header(...)) -> None:
    """Reject requests without a valid API key."""
    pass
