from flask import flash, redirect, render_template, url_for
from flask_login import login_user

from . import bp
from .forms import LoginForm
from ..models import User


@bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        if form.username.data == "admin" and form.password.data == "letmein":
            login_user(User.get_admin())
            return redirect(url_for("dashboard.index"))
        flash("Invalid credentials")
    return render_template("login.html", form=form)
