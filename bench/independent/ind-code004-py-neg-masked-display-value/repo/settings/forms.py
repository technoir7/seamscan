def apply_smtp(form: dict, current: str) -> str:
    if form["smtp_password"] != "********":
        return form["smtp_password"]
    return current
