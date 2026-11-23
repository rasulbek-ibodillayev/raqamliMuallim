from flask import Blueprint, render_template, request, url_for
from flask_babel import gettext as _

from .. import mock as m
from . import account
from ..forms import OBJECTION_REASONS, REGIONS, field, required, respond, validate

bp = Blueprint("user", __name__, url_prefix="/app")


def _recommended():
    from flask_login import current_user

    from ..services import catalog
    rows = catalog.recommended_lessons(current_user.id)
    for r in rows:
        r["url"] = (url_for("user.lesson_topic", topic_id=r["topic_id"], _anchor=f"k{r['sid']}") if r["has_lesson"]
                    else url_for("user.topic", topic_id=r["topic_id"]))
    return rows


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
                           motto=motto, next_state=state, recommended=_recommended())


@bp.get("/diagnostika")
def diagnostic():
    lessons, minutes = m.diagnostic_estimate()
    return render_template("user/diagnostic.html", lessons=lessons, minutes=minutes)


@bp.get("/diagnostika/natija")
def diagnostic_result():
    """Oxirgi diagnostika natijasi (bazadan). Topshirilmagan bo'lsa — ishlab chiqishda namuna, aks holda taklif sahifasi."""
    from flask import redirect
    from flask_login import current_user

    from ..services import attempts as at
    from ..services import catalog
    from .test import is_dev, review_of, sample_review
    last = at.finished(current_user.id, "diagnostic", limit=1)
    if last:
        sections = catalog.attempt_by_section(last[0])
        topics = sum(s["topics"] for s in sections)
        known = sum(s["known"] for s in sections)
        return render_template("user/diagnostic_result.html", pct=int(last[0].score_pct), sections=sections, topics=topics,
                               known=known, questions=review_of(last[0]), advice=at.advice(last[0]))
    if not is_dev():
        return redirect(url_for("user.diagnostic"))
    return render_template("user/diagnostic_result.html", pct=64, sections=m.SECTIONS, topics=42, known=18,
                           questions=sample_review())


@bp.get("/bilim")
def knowledge():
    """«Bilim darajasi» bo'limi olib tashlandi: holat va foizlar endi «O'quv reja»da. Eski havolalar uchun yo'naltirish."""
    from flask import redirect
    return redirect(url_for("user.plan"), 301)


@bp.get("/bilim/<int:topic_id>")
def topic(topic_id):
    """Mavzu: kichik mavzular va foydalanuvchining ular bo'yicha natijasi (bazadan)."""
    from flask import abort
    from flask_login import current_user

    from ..services import catalog
    t = catalog.topic_view(topic_id, current_user.id)
    if t is None:
        abort(404)
    return render_template("user/topic.html", t=t, status=m.STATUS, pass_pct=catalog.PASS_PCT)


@bp.get("/dars/<int:topic_id>")
def lesson_topic(topic_id):
    """Mavzu darsi: kichik mavzular va ularning bloklari bazadan (content_blocks)."""
    from flask import abort

    from ..services import catalog
    from flask_login import current_user
    lesson = catalog.lesson_view(topic_id)
    if lesson is None or not lesson["parts"]:
        abort(404)
    # Har dars testining eng yaxshi natijasi: joriy dars testi ≥ 70% bo'lmaguncha keyingi darslar ko'rsatilmaydi
    scores = catalog.lesson_scores(current_user.id, topic_id)
    pcts = [scores.get(p["id"]) for p in lesson["parts"]]
    return render_template("user/lesson_topic.html", lesson=lesson, pcts=pcts, open_n=open_lessons(pcts),
                           all_passed=all(p is not None and p >= m.PASS_MIN for p in pcts))


@bp.get("/reja")
def plan():
    plan = list(m.LEARN_PLAN)
    if request.args.get("oylik"):
        cur = next(i for i, x in enumerate(plan) if x.get("state") == "current")
        plan.insert(cur + 1, m.MONTHLY_DUE)
    return render_template("user/plan.html", plan=plan, s=m.PLAN_SUMMARY, test_types=m.TEST_TYPES,
                           mandatory=m.MANDATORY_TYPES, decide=m.lesson_decision,
                           pass_min=m.PASS_MIN, solid_min=m.SOLID_MIN)


def open_lessons(pcts, pass_pct=m.PASS_MIN):
    """Nechta dars ko'rinadi: dars testi muvaffaqiyatli (≥ 70%) topshirilganlari va undan keyingi bitta (joriy) dars.
    Joriy dars testi topshirilmaguncha keyingi darslar ko'rsatilmaydi."""
    n = 0
    for p in pcts:
        n += 1
        if p is None or p < pass_pct:
            break
    return n


@bp.get("/dars")
def lesson():
    retry = request.args.get("holat") == "qayta"
    topic = next(t for t in m.LEARN_PLAN if t.get("state") == "current")
    # Qayta o'zlashtirish namunasi — barcha dars testlari topshirilgan mavzu
    pcts = [100, 86, 92, 100] if retry else [l["pct"] for l in topic["lessons"]]
    return render_template("user/lesson.html", retry=retry, audio=bool(request.args.get("audio")),
                           pcts=pcts, open_n=open_lessons(pcts),
                           all_passed=all(p is not None and p >= m.PASS_MIN for p in pcts))


@bp.get("/tutor")
def tutor():
    return render_template("user/tutor.html", topic=request.args.get("mavzu") or m.CURRENT_TOPIC)


def _tests_ctx(**extra):
    """«Testlar» sahifasi: yakunlanmagan urinishlar bazadan; majburiy testlar jadvali hozircha namunaviy (5b)."""
    from flask_login import current_user

    from ..services import attempts as at
    from ..services import test_builder as tb
    from ..services.timefmt import day_month, now
    from .test import attempt_url, is_dev, type_names, weekly_open
    rows = tb.unfinished(current_user.id)
    names = at.names(rows, type_names())
    unfinished = []
    for a in rows:
        done = sum(1 for i in a.items if (i.answer or {}).get("v") not in (None, "", []))
        unfinished.append({"key": str(a.client_uuid), "type": a.kind, "name": names[a.id], "url": attempt_url(a),
                           "note": _("%(d)s / %(t)s savol · javoblar saqlangan", d=done, t=a.total),
                           "pct": round(100 * done / a.total) if a.total else 0})
    # /ekranlar namunasi: yakunlanmagan majburiy (oylik) test
    if is_dev() and request.args.get("oylik"):
        unfinished.insert(0, {**m.UNFINISHED_MONTHLY, "url": url_for("test.question", turi="oylik")})
    from datetime import timedelta
    today = now()
    sunday = weekly_open() and not (is_dev() and request.args.get("kun") == "boshqa")
    return {"unfinished": unfinished, "test_types": m.TEST_TYPES, "info": m.TEST_TYPE_INFO, "sunday": sunday,
            "next_sunday": day_month(today + timedelta(days=(6 - today.weekday()) % 7 or 7)), "mandatory": tb.MANDATORY,
            "schedule": m.MANDATORY_SCHEDULE,
            "blocker": next((t for t in unfinished if t["type"] in tb.MANDATORY), None), **extra}


@bp.get("/testlar")
def tests():
    """«Testlar»: yakunlanmagan testlarni davom ettirish va Attestatsiya / Haftalik / Ixtiyoriy testni boshlash.
    Haftalik test faqat yakshanba kuni ochiq."""
    return render_template("user/tests.html", **_tests_ctx())


@bp.post("/testlar/<uuid:key>/bekor")
def test_cancel(key):
    """Yakunlanmagan IXTIYORIY testni bekor qilish (javoblar o'chiriladi). Majburiy testni bekor qilib bo'lmaydi."""
    from flask_login import current_user

    from ..services import attempts as at
    from ..services import test_builder as tb
    a = at.get(key, lock=True)
    error = None
    if a is None or a.user_id != current_user.id or a.status != "in_progress":
        error = _("Test topilmadi")
    elif a.kind in tb.MANDATORY:
        error = _("Majburiy testni bekor qilib bo‘lmaydi — uni yakunlang")
    if error:
        return respond(errors={"key": error}, template="user/tests.html", **_tests_ctx())
    at.cancel(a)
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
    from flask_login import current_user

    from ..services import catalog
    return render_template("user/optional.html", topics=catalog.optional_topics(current_user.id), status=m.STATUS)


def _result_row(a, names) -> dict:
    from ..services.timefmt import when
    minutes = max(1, round((a.finished_at - a.started_at).total_seconds() / 60))
    return {"id": a.id, "type": a.kind, "name": names[a.id], "when": when(a.finished_at), "pct": int(a.score_pct),
            "decision": a.decision, "n": a.total, "min": minutes}


@bp.get("/natijalar")
def results():
    from flask_login import current_user

    from ..services import attempts as at
    from .test import is_dev, type_names
    rows = [] if is_dev() and request.args.get("bosh") else at.finished(current_user.id, limit=300)
    names = at.names(rows, type_names())
    return render_template("user/results.html", results=[_result_row(a, names) for a in rows],
                           decision=m.DECISION, test_types=m.TEST_TYPES)


@bp.get("/natijalar/<int:rid>")
def result_detail(rid):
    """Yakunlangan test: har bir savol va javob (xato — qizil, to'g'ri javob — yashil) va qayta topshirish."""
    from flask import abort
    from flask_login import current_user

    from ..extensions import db
    from ..models import TestAttempt
    from ..services import attempts as at
    from .test import retry_url, review_of, sample_review, type_names
    a = db.session.get(TestAttempt, rid)
    if a is not None and a.user_id == current_user.id and a.status == "submitted":
        return render_template("user/result_detail.html", r=_result_row(a, at.names([a], type_names())),
                               questions=review_of(a), decision=m.DECISION, test_types=m.TEST_TYPES,
                               staged=at.is_staged(a), retry=retry_url(a), sample=False,
                               advice=at.advice(a) if at.is_staged(a) else None)
    # O'quv reja va bosh sahifa hali namunaviy (5b): ulardagi natija havolalari (id ≥ m.MOCK_RID) namunani ochadi
    r = next((x for x in m.RESULTS if x["id"] == rid), None)
    if not r:
        abort(404)
    from .test import SLUG_OF
    retry = url_for("test.exam") if r["type"] == "exam" else url_for("test.question", turi=SLUG_OF.get(r["type"], "mavzu"))
    return render_template("user/result_detail.html", r=r, questions=sample_review(), decision=m.DECISION,
                           test_types=m.TEST_TYPES, staged=r["type"] in m.STAGED_TYPES, retry=retry, sample=True)


@bp.get("/xatolar")
def errors():
    return render_template("user/errors.html", recommended=_recommended(), items=m.ERRORS_LIST)


@bp.get("/eslatmalar")
def notes():
    seed = [{"id": i + 1, "topic": t, "title": "", "text": text, "code": src or "", "when": when}
            for i, (t, text, src, when) in enumerate(m.NOTES)]
    from ..services import catalog
    topics = list(dict.fromkeys([n["topic"] for n in seed] + [t["name"] for t in catalog.topic_titles()]))
    return render_template("user/notes.html", notes=seed, topics=topics, current_topic=m.CURRENT_TOPIC)


@bp.get("/muhokamalar")
def discussions():
    return render_template("user/discussions.html", items=m.DISCUSSIONS)


@bp.get("/muhokama")
def discussion():
    return render_template("user/discussion.html", msgs=m.DISCUSSION)


def _objections_ctx():
    from flask_login import current_user

    from ..services import objections as ob
    return {"items": ob.mine(current_user.id), "state": m.OBJ_STATE}


def _objection_fields() -> dict:
    errors = validate({
        "reason": (field("reason"), lambda v: None if v in OBJECTION_REASONS else _("Sababni tanlang")),
        "note": (field("note"), lambda v: None if len(v) <= 1000 else _("Izoh 1000 belgidan oshmasin")),
    })
    if not errors and field("reason") == "other" and not field("note"):
        errors = {"note": _("«Boshqa» sababini izohda yozing")}
    return errors


@bp.get("/etirozlarim")
def objections():
    return render_template("user/objections.html", **_objections_ctx())


@bp.post("/etirozlarim/<int:oid>/tahrir")
def objection_edit(oid):
    """Hali ko'rib chiqilmagan e'tirozning sababi va izohini o'zgartirish."""
    from flask_login import current_user

    from ..extensions import db
    from ..services import objections as ob
    o = ob.own(current_user.id, oid)
    if o is None:
        errors = {"reason": _("E’tiroz topilmadi")}
    elif o.status != "review":
        errors = {"reason": _("Ko‘rib chiqilgan e’tirozni o‘zgartirib bo‘lmaydi")}
    else:
        errors = _objection_fields()
    if not errors:
        o.reason, o.text = field("reason"), field("note")
        db.session.commit()
    return respond(errors=errors, template="user/objections.html", **_objections_ctx(),
                   redirect_to=url_for("user.objections"), message=_("E’tiroz yangilandi"))


@bp.post("/etirozlarim/<int:oid>/ochirish")
def objection_delete(oid):
    """Hali ko'rib chiqilmagan e'tirozni o'chirish. Ko'rib chiqilgani (qabul/rad) o'chirilmaydi."""
    from flask_login import current_user

    from ..extensions import db
    from ..services import objections as ob
    o = ob.own(current_user.id, oid)
    errors = None
    if o is None:
        errors = {"id": _("E’tiroz topilmadi")}
    elif o.status != "review":
        errors = {"id": _("Ko‘rib chiqilgan e’tirozni o‘chirib bo‘lmaydi")}
    else:
        db.session.delete(o)
        db.session.commit()
    return respond(errors=errors, template="user/objections.html", **_objections_ctx(),
                   redirect_to=url_for("user.objections"), message=_("E’tiroz o‘chirildi"))


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
    if not errors:
        from flask_login import current_user

        from ..extensions import db
        current_user.region = field("region")
        db.session.commit()
    return respond(errors=errors, template=PROFILE_TPL, **account.context("user", "user", open="reg"),
                   redirect_to=url_for("user.profile"), message=_("Hudud saqlandi"))


@bp.post("/etiroz")
def objection_create():
    """Test davomida yoki natija sahifasida savolga e'tiroz (services/objections.py).
    "namuna:…" — /ekranlar dagi namunaviy savol: tekshiriladi, lekin saqlanmaydi (faqat ishlab chiqishda)."""
    from flask_login import current_user

    from ..services import objections as ob
    from .test import is_dev
    errors = {**validate({"question": (field("question"), required)}), **_objection_fields()}
    if not errors and not (is_dev() and field("question").startswith("namuna:")):
        try:
            ob.create(current_user.id, field("question"), field("reason"), field("note"), field("urgent") == "1")
        except ob.ObjectionError as e:
            errors = {"reason": str(e)}
    return respond(errors=errors, template="user/objections.html", **_objections_ctx(),
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
