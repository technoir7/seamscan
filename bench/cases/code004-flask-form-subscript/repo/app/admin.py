from flask import Flask, redirect, render_template, request, session

app = Flask(__name__)


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form["password"] == "admin123":
            session["is_admin"] = True
            return redirect("/admin")
        return render_template("login.html", error="Wrong password")
    return render_template("login.html")
