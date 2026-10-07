def normalize_username(raw: str) -> str:
    return raw.replace("​", "").strip().lower()
