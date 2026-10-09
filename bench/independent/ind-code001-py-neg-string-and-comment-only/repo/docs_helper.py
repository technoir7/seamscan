def explain() -> str:
    """Never pass verify=False to requests.get in production code."""
    # ssl.CERT_NONE would disable certificate checks; we use the default instead.
    return "see security guide"
