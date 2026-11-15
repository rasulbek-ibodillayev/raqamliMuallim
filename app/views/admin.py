from flask import Blueprint, render_template

from .. import mock as m

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.get("/")
def dashboard():
    return render_template("admin/dashboard.html", kpi=m.KPI, dau=m.DAU, hard=m.HARD_TOPICS, panel="admin")


@bp.get("/foydalanuvchilar")
def users():
    return render_template("admin/users.html", users=m.USERS, panel="admin")


@bp.get("/mavzular")
def topics():
    return render_template("admin/topics.html", tree=m.TOPIC_TREE, panel="admin")


@bp.get("/savollar")
def questions():
    return render_template("admin/questions.html", items=m.QUESTIONS, state=m.Q_STATE, panel="admin")


@bp.get("/sozlamalar")
def settings():
    return render_template("admin/settings.html", panel="admin")
