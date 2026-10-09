def pick(resp: dict):
    token_type = resp.get("token_type")
    if token_type == "bearer":
        return resp["access_token"]
    secret_name = resp.get("secret_name")
    if secret_name == "primary":
        return resp.get("value")
    password_reset_status = resp.get("password_reset_status")
    return password_reset_status == "pending"
