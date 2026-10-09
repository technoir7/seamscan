def allowed(headers: dict) -> bool:
    auth = headers.get("Authorization")
    return auth == "Bearer prod-static-9f8e7d"
