from flask import Blueprint, render_template, request, url_for
from flask_babel import gettext as _

from .. import mock as m
from ..forms import (OBJECTION_REASONS, REGIONS, check_email, check_name, check_password, field, required, respond,
                     validate)

bp = Blueprint("user", __name__, url_prefix="/app")


@bp.get("/")
def home():
    new_user = bool(request.args.get("yangi"))
    done_steps = int(request.args.get("qadam", 0))  # namunada: nechta qadam bajarilgan
    return render_template("user/home.html", sections=m.SECTIONS, r=m.READINESS, rstate=m.READINESS_STATE,
                           today=m.TODAY, onboarding=m.ONBOARDING, new_user=new_user, done_steps=done_steps)


@bp.get("/diagnostika")
def diagnostic():
    return render_template("user/diagnostic.html")


@bp.get("/diagnostika/natija")
def diagnostic_result():
    return render_template("user/diagnostic_result.html", sections=m.SECTIONS, dist=m.DISTRIBUTION,
                           status=m.STATUS, plan=m.PLAN)


@bp.get("/bilim")
def knowledge():
    return render_template("user/knowledge.html", sections=m.SECTIONS, dist=m.DISTRIBUTION,
                           status=m.STATUS, view=request.args.get("view", "royxat"))


@bp.get("/bilim/<int:topic_id>")
def topic(topic_id):
    return render_template("user/topic.html", t=m.TOPIC, status=m.STATUS)


@bp.get("/reja")
def plan():
    return render_template("user/plan.html", plan=m.PLAN)


@bp.get("/dars")
def lesson():
    return render_template("user/lesson.html", retry=request.args.get("holat") == "qayta",
                           audio=bool(request.args.get("audio")))


@bp.get("/tutor")
def tutor():
    return render_template("user/tutor.html")


@bp.get("/testlarim")
def tests():
    return render_template("user/tests.html")


@bp.get("/nazorat")
def control():
    return render_template("user/control.html")


@bp.get("/ixtiyoriy-test")
def optional():
    return render_template("user/optional.html", topics=m.OPTIONAL_TOPICS, status=m.STATUS)


@bp.get("/natijalar")
def results():
    empty = bool(request.args.get("bosh"))
    return render_template("user/results.html", results=[] if empty else m.RESULTS,
                           decision=m.DECISION, trend=m.TREND)


@bp.get("/xatolar")
def errors():
    return render_template("user/errors.html", weak=m.ERRORS_WEAK, items=m.ERRORS_LIST)


@bp.get("/eslatmalar")
def notes():
    seed = [{"id": i + 1, "topic": t, "title": "", "text": text, "code": src or "", "when": when}
            for i, (t, text, src, when) in enumerate(m.NOTES)]
    topics = list(dict.fromkeys([n["topic"] for n in seed] +
                                [t["name"] for s in m.SECTIONS for t in s["topics"]]))
    return render_template("user/notes.html", notes=seed, topics=topics)


@bp.get("/muhokamalar")
def discussions():
    return render_template("user/discussions.html", items=m.DISCUSSIONS)


@bp.get("/muhokama")
def discussion():
    return render_template("user/discussion.html", msgs=m.DISCUSSION)


@bp.get("/etirozlarim")
def objections():
    return render_template("user/objections.html", items=m.OBJECTIONS, state=m.OBJ_STATE)


@bp.get("/sertifikatlar")
def certificates():
    return render_template("user/certificates.html", topics=m.CERT_TOPICS)


@bp.get("/sertifikat/INF-2026-000123")
def certificate_print():
    return render_template("user/certificate_print.html", topics=m.CERT_TOPICS)


@bp.get("/profil")
def profile():
    return render_template("user/profile.html")


@bp.get("/yana")
def more():
    return render_template("user/more.html")


@bp.get("/yordam")
def help():
    return render_template("user/help.html")


@bp.get("/oflayn")
def offline():
    return render_template("user/offline.html")


# ---------- Formalar (POST). Tekshiruv: app/forms.py ----------


@bp.post("/profil/malumotlar")
def profile_info():
    email = field("email").lower()
    errors = validate({
        "fn": (field("fn"), lambda v: check_name(v, "first")),
        "ln": (field("ln"), lambda v: check_name(v, "last")),
        "email": (email, lambda v: check_email(v) if v else None),
    })
    return respond(errors=errors, template="user/profile.html", open="info",
                   redirect_to=url_for("user.profile"), message=_("Shaxsiy ma’lumotlar saqlandi"))


@bp.post("/profil/parol")
def profile_password():
    new = request.form.get("new", "")
    errors = validate({
        "old": (request.form.get("old", ""), required),
        "new": (new, check_password),
        "new2": (request.form.get("new2", ""), lambda v: None if v == new else _("Parollar bir xil emas")),
    })
    if not errors and request.form.get("old") == new:
        errors = {"new": _("Yangi parol joriy paroldan farq qilsin")}
    return respond(errors=errors, template="user/profile.html", open="pw",
                   redirect_to=url_for("user.profile"), message=_("Parol o‘zgartirildi"))


@bp.post("/profil/hudud")
def profile_region():
    errors = validate({"region": (field("region"), lambda v: None if v in REGIONS else _("Viloyatni ro‘yxatdan tanlang"))})
    return respond(errors=errors, template="user/profile.html", open="reg",
                   redirect_to=url_for("user.profile"), message=_("Hudud saqlandi"))


@bp.post("/etiroz")
def objection_create():
    """Natija sahifasi va attestatsiya sinovidan e'tiroz. Backendda: objections jadvali, ekspert navbati."""
    errors = validate({
        "question": (field("question"), required),
        "reason": (field("reason"), lambda v: None if v in OBJECTION_REASONS else _("Sababni tanlang")),
        "note": (field("note"), lambda v: None if len(v) <= 1000 else _("Izoh 1000 belgidan oshmasin")),
    })
    if not errors and field("reason") == "other" and not field("note"):
        errors = {"note": _("«Boshqa» sababini izohda yozing")}
    return respond(errors=errors, template="test/result.html", failed=False, review=m.REVIEW,
                   redirect_to=url_for("user.objections"),
                   message=_("E’tirozingiz qabul qilindi. Ekspert xulosasi «E’tirozlarim» bo‘limida ko‘rinadi"))


@bp.post("/muhokama")
def discussion_reply():
    body = field("body")
    errors = validate({"body": (body, lambda v: _("Xabarni yozing") if len(v) < 2 else
                                (None if len(v) <= 2000 else _("Xabar 2000 belgidan oshmasin")))})
    return respond(errors=errors, template="user/discussion.html", msgs=m.DISCUSSION,
                   redirect_to=url_for("user.discussion"), message=_("Fikringiz qo‘shildi"),
                   data={"author": f"{m.ME['first']} {m.ME['last']}", "when": "Hozir", "body": body})


@bp.post("/eslatmalar")
def notes_save():
    """Eslatmalar hozircha brauzerda saqlanadi; server tekshiradi va backendda shu yerga yozadi."""
    errors = validate({
        "topic": (field("topic"), required),
        "text": (field("text"), lambda v: _("Qaydni yozing") if not v else (None if len(v) <= 5000 else _("Qayd 5000 belgidan oshmasin"))),
        "code": (field("code"), lambda v: None if len(v) <= 5000 else _("Kod 5000 belgidan oshmasin")),
    })
    return respond(errors=errors, template="user/notes.html", notes=[], topics=[],
                   redirect_to=url_for("user.notes"), message=_("Eslatma saqlandi"))
