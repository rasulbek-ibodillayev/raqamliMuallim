"""Ekspert paneli: kontent va uning sifati — ekspertning vazifalari.

Tekshiruv navbati, Savollar banki, Savol yaratish, Mavzular va darslar, E'tirozlar.
"""
from flask import Blueprint, render_template, request

from .. import mock as m

bp = Blueprint("expert", __name__, url_prefix="/ekspert")


@bp.get("/")
def queue():
    return render_template("expert/queue.html", items=m.QUEUE, panel="expert")


@bp.get("/savollar")
def questions():
    return render_template("expert/questions.html", items=m.QUESTIONS, state=m.Q_STATE, panel="expert")


@bp.get("/savol")
def editor():
    return render_template("expert/editor.html", panel="expert")


@bp.get("/mavzular")
def topics():
    names = [t for _, ts in m.TOPIC_TREE for t, _ in ts]
    selected = request.args.get("mavzu") if request.args.get("mavzu") in names else "Python: shart operatorlari"
    return render_template("expert/topics.html", tree=m.TOPIC_TREE, selected=selected, panel="expert")


@bp.get("/etirozlar")
def objections():
    return render_template("expert/objections.html", items=m.EXPERT_OBJ, panel="expert")
