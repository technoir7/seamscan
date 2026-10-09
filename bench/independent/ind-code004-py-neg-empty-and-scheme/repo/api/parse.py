def parse_auth(header: str):
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer":
        return None
    return token


def validate(password: str):
    if password == "":
        raise ValueError("password required")
