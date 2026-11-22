"""Ekspert paneli: kontent va uning sifati — ekspertning vazifalari.

- Savollar banki (bosh sahifa): ichida ikki karta — «Tekshiruv navbati» (AI tuzgan savollar) va «Savol qo'shish».
- Tekshiruv navbati: AI har bir mavzu va dars bo'yicha tuzgan savollar. Ekspert savol va javoblarni tahrirlab,
  tasdiqlaydi (bankka qo'shiladi) yoki rad etadi (avtomatik o'chiriladi). Sahifalash bilan.
- Savol qo'shish: mavzu, dars, qiyinlik, savol turi, vaqt, format (matn/chizma/jadval/rasm), savol va javoblar.
- Mavzular va darslar: avval mavzu, so'ng uning ichida istalgancha dars; dars bloklari va havolalar.
- E'tirozlar.
"""
from flask import Blueprint, redirect, render_template, request, url_for
from flask_babel import gettext as _

from .. import mock as m
from ..forms import field, required, respond, validate

bp = Blueprint("expert", __name__, url_prefix="/ekspert")

QUEUE_PAGE = 5


def _ctx(**extra):
    return {"panel": "expert", "kinds": m.Q_KINDS, "formats": m.Q_FORMATS, "levels": m.Q_LEVELS,
            "content": m.EXPERT_CONTENT, **extra}


@bp.get("/")
def questions():
    return render_template("expert/questions.html", items=m.QUESTIONS, state=m.Q_STATE, queue_n=len(m.AI_QUEUE), **_ctx())


@bp.get("/savollar")
def questions_old():
    return redirect(url_for("expert.questions"), 301)


@bp.get("/navbat")
def queue():
    # Filtrlar (GET): qidiruv, mavzu, dars, daraja — sahifalashdan oldin qo'llanadi
    f = {k: request.args.get(k, "").strip() for k in ("q", "mavzu", "dars", "daraja")}
    found = [x for x in m.AI_QUEUE
             if (not f["q"] or f["q"].lower() in x["text"].lower())
             and (not f["mavzu"] or x["topic"] == f["mavzu"])
             and (not f["dars"] or x["lesson"] == f["dars"])
             and (not f["daraja"] or x["level"] == f["daraja"])]
    try:
        page = max(1, int(request.args.get("sahifa", 1)))
    except ValueError:
        page = 1
    pages = max(1, -(-len(found) // QUEUE_PAGE))
    page = min(page, pages)
    items = found[(page - 1) * QUEUE_PAGE: page * QUEUE_PAGE]
    lessons = next((t["lessons"] for t in m.EXPERT_CONTENT if t["name"] == f["mavzu"]), None)
    return render_template("expert/queue.html", items=items, page=page, pages=pages, total=len(m.AI_QUEUE),
                           found=len(found), f=f, lessons=lessons, **_ctx())


@bp.post("/navbat/<int:qid>")
def queue_decide(qid):
    """Tasdiqlash (tahrirlangan holda) yoki rad etish. Backendda: tasdiq — questions.status='approved',
    rad — savol o'chiriladi (audit_log'ga yoziladi)."""
    action = field("action")
    if action == "reject":
        return respond(redirect_to=url_for("expert.queue"), message=_("Savol rad etildi va o‘chirildi"))
    errors = validate({"text": (field("text"), lambda v: required(v, _("Savol matnini kiriting")))})
    opts = [o.strip() for o in request.form.getlist("opt") if o.strip()]
    if not errors and request.form.get("type") != "ochiq" and len(opts) < 2:
        errors = {"opt": _("Kamida 2 ta javob varianti bo‘lsin")}
    if not errors and not request.form.getlist("right"):
        errors = {"opt": _("To‘g‘ri javobni belgilang")}
    return respond(errors=errors, template="expert/queue.html", items=m.AI_QUEUE[:QUEUE_PAGE], page=1,
                   pages=1, total=len(m.AI_QUEUE), found=len(m.AI_QUEUE), f={}, lessons=None, **_ctx(),
                   redirect_to=url_for("expert.queue"), message=_("Savol tasdiqlandi va savollar bankiga qo‘shildi"))


@bp.get("/savol")
def editor():
    return render_template("expert/editor.html", **_ctx())


@bp.post("/savol")
def editor_save():
    """Yangi savol. Turi bo'yicha javoblar: yopiq — bitta to'g'ri; ko'p javobli — bir nechta to'g'ri;
    moslashtirish — juftliklar; ochiq — to'g'ri javob matni."""
    kind = field("kind")
    rules = {
        "topic": (field("topic"), lambda v: required(v, _("Mavzuni tanlang"))),
        "lesson": (field("lesson"), lambda v: required(v, _("Darsni tanlang"))),
        "level": (field("level"), lambda v: None if v in m.Q_LEVELS else _("Qiyinlik darajasini tanlang")),
        "kind": (kind, lambda v: None if v in m.Q_KINDS else _("Savol turini tanlang")),
        "format": (field("format"), lambda v: None if v in m.Q_FORMATS else _("Savol formatini tanlang")),
        "time": (field("time"), lambda v: None if v.isdigit() and 10 <= int(v) <= 1800 else _("Vaqt 10–1800 soniya oralig‘ida bo‘lsin")),
        "text": (field("text"), lambda v: required(v, _("Savol matnini kiriting"))),
    }
    errors = validate(rules)
    if not errors:
        if kind == "ochiq":
            if not field("answer"):
                errors = {"answer": _("To‘g‘ri javobni kiriting")}
        elif kind == "moslash":
            left = [x.strip() for x in request.form.getlist("left")]
            right = [x.strip() for x in request.form.getlist("right_txt")]
            if sum(1 for a, b in zip(left, right) if a and b) < 2:
                errors = {"pairs": _("Kamida 2 ta to‘liq juftlik kiriting")}
        else:
            opts = [o.strip() for o in request.form.getlist("opt")]
            marks = request.form.getlist("right")
            if sum(1 for o in opts if o) < 2:
                errors = {"opt": _("Kamida 2 ta javob varianti bo‘lsin")}
            elif not marks:
                errors = {"opt": _("To‘g‘ri javobni belgilang")}
            elif kind == "kop" and len(marks) < 2:
                errors = {"opt": _("Ko‘p javobli savolda kamida 2 ta to‘g‘ri javob bo‘lsin")}
    return respond(errors=errors, template="expert/editor.html", **_ctx(),
                   redirect_to=url_for("expert.questions"), message=_("Savol saqlandi va savollar bankiga qo‘shildi"))


@bp.post("/savollar/<int:idx>/ochirish")
def question_delete(idx):
    return respond(redirect_to=url_for("expert.questions"), message=_("Savol o‘chirildi"))


@bp.get("/mavzular")
def topics():
    return render_template("expert/topics.html", block_kinds=[(k, i, str(l)) for k, i, l in m.BLOCK_KINDS], **_ctx())


@bp.get("/etirozlar")
def objections():
    return render_template("expert/objections.html", items=m.EXPERT_OBJ, panel="expert")
