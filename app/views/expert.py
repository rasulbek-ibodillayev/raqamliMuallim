from flask import Blueprint, render_template

from .. import mock as m

bp = Blueprint("expert", __name__, url_prefix="/ekspert")


@bp.get("/")
def queue():
    return render_template("expert/queue.html", items=m.QUEUE, panel="expert")


@bp.get("/savol")
def editor():
    return render_template("expert/editor.html", panel="expert")


@bp.get("/etirozlar")
def objections():
    return render_template("expert/objections.html", items=m.EXPERT_OBJ, panel="expert")
