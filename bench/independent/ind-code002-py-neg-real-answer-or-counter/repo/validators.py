def is_valid_email(s: str) -> bool:
    try:
        local, domain = s.split("@")
        return bool(local and "." in domain)
    except Exception:
        return False


def parse_all(rows):
    failed = 0
    out = []
    for r in rows:
        try:
            out.append(int(r))
        except Exception:
            failed += 1
            continue
    return out, failed
