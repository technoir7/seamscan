from jwt import decode


def authenticate_socket(query_params: dict) -> str:
    token = query_params.get("token", "")
    payload = decode(
        token,
        options={"verify_signature": False, "verify_exp": False},
    )
    return payload["sub"]
