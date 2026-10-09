from auth.backends import verify_password


def try_login(user, pw) -> bool:
    ok = False
    try:
        ok = verify_password(user, pw)
    except BaseException:
        ...
    return ok
