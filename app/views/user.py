from flask import Blueprint, render_template, request, url_for
from flask_babel import gettext as _

from .. import mock as m
from . import account
from ..forms import OBJECTION_REASONS, REGIONS, field, required, respond, validate

bp = Blueprint("user", __name__, url_prefix="/app")


@bp.get("/")
def home():
    import random
    from flask import session
    new_user = bool(request.args.get("yangi"))
    done_steps = request.args.get("qadam", 0, type=int) or 0  # namunada: nechta qadam bajarilgan (noto'g'ri qiymat — 0)
    # Motivatsion so'z har kirishda yangidan tanlanadi (kirishda sessiyadan o'chiriladi)
    if "motto" not in session:
        session["motto"] = random.randrange(len(m.MOTTOS))
    motto = m.MOTTOS[session["motto"] % len(m.MOTTOS)]
    # Keyingi qadam holati (backendda: oxirgi faollikdan). Namunada ?holat=tugadi | nazorat
    #  davom — mavzu tugatilmay chiqib ketilgan; tugadi — mavzu yakunlangan; nazorat — majburiy nazorat navbati
    state = request.args.get("holat", "davom")
    today = list(m.TODAY) + ([m.TODAY_CONTROL] if state == "nazorat" else [])
    return render_template("user/home.html", sections=m.SECTIONS, r=m.READINESS, rstate=m.READINESS_STATE,
                           today=today, onboarding=m.ONBOARDING, new_user=new_user, done_steps=done_steps,
                           motto=motto, next_state=state, weak=m.HOME_ERRORS)


@bp.get("/diagnostika")
def diagnostic():
    return render_template("user/diagnostic.html")


@bp.get("/diagnostika/natija")
def diagnostic_result():
    return render_template("user/diagnostic_result.html", sections=m.SECTIONS, dist=m.DISTRIBUTION,
                           status=m.STATUS, plan=[p for p in m.LEARN_PLAN if p["kind"] == "topic"],
                           excluded=m.PLAN_EXCLUDED, questions=m.RESULT_QUESTIONS)


@bp.get("/bilim")
def knowledge():
    """«Bilim darajasi» bo'limi olib tashlandi: holat va foizlar endi «O'quv reja»da. Eski havolalar uchun yo'naltirish."""
    from flask import redirect
    return redirect(url_for("user.plan"), 301)


@bp.get("/bilim/<int:topic_id>")
def topic(topic_id):
    return render_template("user/topic.html", t=m.TOPIC, status=m.STATUS)


@bp.get("/reja")
def plan():
    plan = list(m.LEARN_PLAN)
    if request.args.get("oylik"):
        cur = next(i for i, x in enumerate(plan) if x.get("state") == "current")
        plan.insert(cur + 1, m.MONTHLY_DUE)
    return render_template("user/plan.html", plan=plan, s=m.PLAN_SUMMARY, dist=m.DISTRIBUTION, status=m.STATUS,
                           excluded=m.PLAN_EXCLUDED, diag=request.args.get("diagnostika") != "yoq",
                           test_types=m.TEST_TYPES, pass_min=m.PASS_MIN, solid_min=m.SOLID_MIN)


@bp.get("/dars")
def lesson():
    return render_template("user/lesson.html", retry=request.args.get("holat") == "qayta",
                           audio=bool(request.args.get("audio")))


@bp.get("/tutor")
def tutor():
    return render_template("user/tutor.html", topic=request.args.get("mavzu") or m.CURRENT_TOPIC)


@bp.get("/testlar")
def tests():
    """«Testlar»: yakunlanmagan testlarni davom ettirish va Attestatsiya / Haftalik / Ixtiyoriy testni boshlash.
    Haftalik test faqat yakshanba kuni ochiq (namunada ?kun=yakshanba)."""
    # Namunada bugun yakshanba (haftalik test ochiq); ?kun=boshqa — boshqa kun
    sunday = request.args.get("kun") != "boshqa"
    unfinished = ([m.UNFINISHED_MONTHLY] if request.args.get("oylik") else []) + m.UNFINISHED_TESTS
    blocker = next((t for t in unfinished if t["type"] in m.MANDATORY_TYPES), None)
    return render_template("user/tests.html", unfinished=unfinished, test_types=m.TEST_TYPES, info=m.TEST_TYPE_INFO,
                           sunday=sunday, mandatory=m.MANDATORY_TYPES, schedule=m.MANDATORY_SCHEDULE, blocker=blocker)


@bp.post("/testlar/<key>/bekor")
def test_cancel(key):
    """Yakunlanmagan IXTIYORIY testni bekor qilish (javoblar o'chiriladi). Majburiy testni bekor qilib bo'lmaydi."""
    t = next((x for x in m.UNFINISHED_TESTS + [m.UNFINISHED_MONTHLY] if x["key"] == key), None)
    if not t:
        return respond(errors={"key": _("Test topilmadi")}, template="user/tests.html", unfinished=m.UNFINISHED_TESTS,
                       test_types=m.TEST_TYPES, info=m.TEST_TYPE_INFO, sunday=True, mandatory=m.MANDATORY_TYPES,
                       schedule=m.MANDATORY_SCHEDULE, blocker=None)
    if t["type"] in m.MANDATORY_TYPES:
        return respond(errors={"key": _("Majburiy testni bekor qilib bo‘lmaydi — uni yakunlang")}, template="user/tests.html",
                       unfinished=m.UNFINISHED_TESTS, test_types=m.TEST_TYPES, info=m.TEST_TYPE_INFO, sunday=True,
                       mandatory=m.MANDATORY_TYPES, schedule=m.MANDATORY_SCHEDULE, blocker=None)
    return respond(redirect_to=url_for("user.tests"), message=_("Test bekor qilindi"))


@bp.get("/testlarim")
def tests_old():
    from flask import redirect
    return redirect(url_for("user.tests"), 301)


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
                           decision=m.DECISION, trend=m.TREND, test_types=m.TEST_TYPES, info=m.TEST_TYPE_INFO)


@bp.get("/natijalar/<int:rid>")
def result_detail(rid):
    """Yakunlangan test: har bir savol va javob (xato — qizil, to'g'ri javob — yashil) va qayta topshirish."""
    from flask import abort
    r = next((x for x in m.RESULTS if x["id"] == rid), None)
    if not r:
        abort(404)
    from .test import TYPE_SLUGS
    slug = next((k for k, v in TYPE_SLUGS.items() if v == r["type"]), "mavzu")
    return render_template("user/result_detail.html", r=r, questions=m.RESULT_QUESTIONS, decision=m.DECISION,
                           test_types=m.TEST_TYPES, staged=r["type"] in m.STAGED_TYPES, slug=slug)


@bp.get("/xatolar")
def errors():
    return render_template("user/errors.html", weak=m.ERRORS_WEAK, items=m.ERRORS_LIST)


@bp.get("/eslatmalar")
def notes():
    seed = [{"id": i + 1, "topic": t, "title": "", "text": text, "code": src or "", "when": when}
            for i, (t, text, src, when) in enumerate(m.NOTES)]
    topics = list(dict.fromkeys([n["topic"] for n in seed] +
                                [t["name"] for s in m.SECTIONS for t in s["topics"]]))
    return render_template("user/notes.html", notes=seed, topics=topics, current_topic=m.CURRENT_TOPIC)


@bp.get("/muhokamalar")
def discussions():
    return render_template("user/discussions.html", items=m.DISCUSSIONS)


@bp.get("/muhokama")
def discussion():
    return render_template("user/discussion.html", msgs=m.DISCUSSION)


@bp.get("/etirozlarim")
def objections():
    return render_template("user/objections.html", items=m.OBJECTIONS, state=m.OBJ_STATE)


@bp.post("/etirozlarim/<int:oid>/tahrir")
def objection_edit(oid):
    """Hali ko'rib chiqilmagan e'tirozning sababi va izohini o'zgartirish."""
    o = next((x for x in m.OBJECTIONS if x["id"] == oid), None)
    ctx = {"template": "user/objections.html", "items": m.OBJECTIONS, "state": m.OBJ_STATE}
    if not o:
        return respond(errors={"reason": _("E’tiroz topilmadi")}, **ctx)
    if o["state"] != "review":
        return respond(errors={"reason": _("Ko‘rib chiqilgan e’tirozni o‘zgartirib bo‘lmaydi")}, **ctx)
    errors = validate({
        "reason": (field("reason"), lambda v: None if v in OBJECTION_REASONS else _("Sababni tanlang")),
        "note": (field("note"), lambda v: None if len(v) <= 1000 else _("Izoh 1000 belgidan oshmasin")),
    })
    if not errors and field("reason") == "other" and not field("note"):
        errors = {"note": _("«Boshqa» sababini izohda yozing")}
    return respond(errors=errors, **ctx, redirect_to=url_for("user.objections"), message=_("E’tiroz yangilandi"))


@bp.post("/etirozlarim/<int:oid>/ochirish")
def objection_delete(oid):
    """Hali ko'rib chiqilmagan e'tirozni o'chirish. Ko'rib chiqilgani (qabul/rad) o'chirilmaydi.
    Backendda: objections.status = 'review' va muallif shu foydalanuvchi bo'lsagina o'chiriladi."""
    o = next((x for x in m.OBJECTIONS if x["id"] == oid), None)
    if not o:
        return respond(errors={"id": _("E’tiroz topilmadi")}, template="user/objections.html", items=m.OBJECTIONS, state=m.OBJ_STATE)
    if o["state"] != "review":
        return respond(errors={"id": _("Ko‘rib chiqilgan e’tirozni o‘chirib bo‘lmaydi")}, template="user/objections.html",
                       items=m.OBJECTIONS, state=m.OBJ_STATE)
    return respond(redirect_to=url_for("user.objections"), message=_("E’tiroz o‘chirildi"))


@bp.get("/sertifikatlar")
def certificates():
    return render_template("user/certificates.html", topics=m.CERT_TOPICS)


@bp.get("/sertifikat/INF-2026-000123")
def certificate_print():
    return render_template("user/certificate_print.html", topics=m.CERT_TOPICS)


@bp.get("/profil")
def profile():
    return render_template(PROFILE_TPL, **account.context("user", "user"))


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


# Profil formalari (ism, telefon/email, parol, maxfiy so'z) — uchala rol uchun umumiy: app/views/account.py
PROFILE_TPL = "user/profile.html"


@bp.post("/profil/malumotlar")
def profile_info():
    return account.save_info("user", "user", PROFILE_TPL)


@bp.post("/profil/parol-tekshirish")
def password_check():
    return account.password_check()


@bp.post("/profil/aloqa/kod")
def contact_code():
    return account.contact_code("user", "user", PROFILE_TPL)


@bp.post("/profil/aloqa/tasdiq")
def contact_confirm():
    return account.contact_confirm("user", "user", PROFILE_TPL)


@bp.post("/profil/maxfiy-soz")
def profile_secret():
    return account.save_secret("user", "user", PROFILE_TPL)


@bp.post("/profil/parol")
def profile_password():
    return account.change_password("user", "user", PROFILE_TPL)


@bp.post("/profil/hudud")
def profile_region():
    errors = validate({"region": (field("region"), lambda v: None if v in REGIONS else _("Viloyatni ro‘yxatdan tanlang"))})
    return respond(errors=errors, template=PROFILE_TPL, **account.context("user", "user", open="reg"),
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
    return respond(errors=errors, template="test/result.html", failed=False, questions=m.RESULT_QUESTIONS,
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
    return respond(errors=errors, template="user/notes.html", notes=[], topics=[], current_topic=m.CURRENT_TOPIC,
                   redirect_to=url_for("user.notes"), message=_("Eslatma saqlandi"))
