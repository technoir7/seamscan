from flask import redirect


def do_login(form):
    if form.username.data == "admin" and form.password.data == "S3cretPass!":
        return redirect("/dashboard")
    return redirect("/login")
