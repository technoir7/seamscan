from flask import Blueprint, redirect, request, url_for
from flask_login import current_user, login_required

from .extensions import db
from .models import Task

bp = Blueprint("tasks", __name__)


@bp.route("/tasks", methods=["POST"])
@login_required
def create_task():
    task = Task(title=request.form["title"], owner_id=current_user.id)
    db.session.add(task)
    db.session.commit()
    return redirect(url_for("tasks.index"))


@bp.route("/tasks/<int:task_id>/delete", methods=["POST"])
@login_required
def delete_task(task_id):
    Task.query.filter_by(id=task_id, owner_id=current_user.id).delete()
    db.session.commit()
    return redirect(url_for("tasks.index"))
