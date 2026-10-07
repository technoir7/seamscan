def parse_limit(raw: str | None, default: int = 20) -> int | None:
    if raw is None:
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return max(1, min(value, 100))
