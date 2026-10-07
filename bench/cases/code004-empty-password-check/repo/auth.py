def validate(password):
    if password == "":
        raise ValueError("password required")
    return True
