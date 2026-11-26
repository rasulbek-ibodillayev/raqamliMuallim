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


def _plan_urls(p):
    """Reja elementlariga havolalar (servis URL bilmaydi)."""
    for t in p.topics:
        base = url_for("user.lesson_topic" if t["has_lesson"] else "user.topic", topic_id=t["id"])
        t["url"], t["test_url"] = base, url_for("test.question", turi="mavzu", mavzu=t["id"])
        for x in t["lessons"]:
            x["url"] = f"{base}#k{x['id']}" if x["has_blocks"] else base
            x["test_url"] = url_for("test.question", turi="dars", dars=x["id"]) if x["testable"] else None
    from .test import SLUG_OF
    for i in [*p.items, *p.interims, p.monthly, p.daily, p.final]:
        if i and i["kind"] == "test":
            i["url"] = url_for("user.control") if i["type"] == "interim" else url_for("test.question", turi=SLUG_OF[i["type"]])
    return p


def _my_plan():
    from flask_login import current_user

    from ..services import plan as pl
    from .test import weekly_open
    return _plan_urls(pl.build(current_user, sunday=weekly_open()))


def _item_url(i) -> str:
    from .test import SLUG_OF
    if i.get("rid") and i.get("done"):
        return url_for("user.result_detail", rid=i["rid"])
    if i.get("test") == "interim":
        return url_for("user.control")
    if i.get("test"):
        return url_for("test.question", turi=SLUG_OF[i["test"]])
    if i.get("topic_test"):
        return i["topic_test"]["test_url"]
    if i.get("kind") == "topic_test":
        return i["topic"]["test_url"]
    if i.get("lesson"):
        return i["lesson"]["url"] if i["lesson"]["has_blocks"] or not i["lesson"]["test_url"] else i["lesson"]["test_url"]
    return url_for("user.results")


def _sample(*names) -> bool:
    """/ekranlar namunasi: faqat ishlab chiqishda va shu parametrlardan biri berilganda."""
    from .test import is_dev
    return is_dev() and any(n in request.args for n in ("namuna", *names))


@bp.get("/")
def home():
    import random

    from flask import session
    from flask_login import current_user

    from ..services import plan as pl
    # Motivatsion so'z har kirishda yangidan tanlanadi (kirishda sessiyadan o'chiriladi)
    if "motto" not in session:
        session["motto"] = random.randrange(len(m.MOTTOS))
    motto = m.MOTTOS[session["motto"] % len(m.MOTTOS)]
    if _sample("holat", "yangi", "qadam", "dam", "pwa"):
        return render_template("user/home.html", motto=motto, recommended=_recommended(), **_sample_home())
    p = _my_plan()
    nx = pl.next_step(p)
    nx["url"] = _item_url(nx)
    today = pl.today_items(p)
    for i in today:
        i["url"] = _item_url(i)
    new_user = not p.has_results and p.current is not None
    steps, done_steps = _onboarding(p) if new_user else ([], 0)
    return render_template("user/home.html", motto=motto, r=pl.readiness(current_user, p), rstate=m.READINESS_STATE, nx=nx,
                           today=today, today_sub=p.current["name"] if p.current else None, onboarding=steps,
                           done_steps=done_steps, new_user=new_user, recommended=_recommended())


def _onboarding(p):
    """Yangi foydalanuvchi: 3 qadam. Uchinchisi bajarilgach (dars testi) yo'riqnoma o'rniga reja chiqadi."""
    from flask_login import current_user

    from ..services import attempts as at
    from ..services import catalog
    done = 1 if at.finished(current_user.id, "diagnostic", limit=1) else 0
    lesson = p.current["lessons"][0]
    minutes = catalog.diagnostic_estimate()[1]
    return [{"title": _("Diagnostikadan o‘ting"), "url": url_for("user.diagnostic"),
             "sub": _("≈ %(m)s daqiqa · bilgan mavzularingizni aniqlaymiz", m=minutes)},
            {"title": _("Birinchi darsni o‘qing"), "url": lesson["url"],
             "sub": _("≈ %(m)s daqiqa · rejangizdagi birinchi mavzu", m=lesson["min"])},
            {"title": _("Birinchi dars testini topshiring"), "url": lesson["test_url"] or lesson["url"],
             "sub": _("≈ 3 daqiqa · 3 savol")}], done


def _sample_home():
    """/ekranlar uchun namunaviy bosh sahifa: ?holat=davom|tugadi|nazorat, ?yangi=1&qadam=n."""
    state = request.args.get("holat", "davom")
    nx = {
        "davom": (_("Darsni davom ettirish"), "Python: shart operatorlari", "Dasturlash · 2 / 4 dars", 60,
                  "«elif zanjiri» dars testida natija 40%. Darsni takrorlab, testni qayta topshiring.", url_for("user.lesson"), 12),
        "tugadi": (_("Keyingi mavzu"), "Python: sikllar (for, while)", "Dasturlash · 0 / 3 dars", 0,
                   "Yangi mavzu. Birinchi dars — «for sikli».", url_for("user.lesson"), 45),
        "nazorat": (_("Majburiy nazorat testini boshlash"), "Oraliq sinov testi: 4–6 mavzular", "3 bosqich: oson → o‘rta → qiyin", 0,
                    "Navbatdagi mavzuga o‘tishdan oldin shu test topshiriladi.", url_for("user.control", namuna=1), 35),
    }
    label, title, sub, pct, text, url, mins = nx.get(state, nx["davom"])
    today = [dict(t, url=url_for(t["endpoint"], **(t.get("args") or {})))
             for t in list(m.TODAY) + ([m.TODAY_CONTROL] if state == "nazorat" else [])]
    steps = [dict(x, url=url_for(x["endpoint"], **(x.get("args") or {}))) for x in m.ONBOARDING]
    return {"r": {**m.READINESS, "pos": 88}, "rstate": m.READINESS_STATE, "today": today, "today_sub": "Python: shart operatorlari",
            "nx": {"label": label, "title": title, "sub": sub, "pct": pct, "text": text, "url": url, "min": mins,
                   "alert": state == "nazorat"},
            "onboarding": steps, "new_user": bool(request.args.get("yangi")),
            "done_steps": request.args.get("qadam", 0, type=int) or 0}


@bp.get("/diagnostika")
def diagnostic():
    from ..services import catalog
    lessons, minutes = catalog.diagnostic_estimate()
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
    # Savoli yo'q dars testsiz: u keyingi darslarni to'smaydi
    testable = {x["id"]: x["testable"] for x in catalog.lessons_by_topic(topic_id).get(topic_id, [])}
    gate = [pct if testable.get(p["id"]) else 100 for p, pct in zip(lesson["parts"], pcts)]
    # Oflayn paket (static/js/offline.js yuklaydi): hamma dars sahifada, keyingisi qurilmada dars testi yakunlangach ochiladi
    pack = None
    if request.headers.get("X-RM-Pack") == "1":
        from ..services import offline
        pack = {sid: url_for("test.attempt", attempt_uuid=u) for sid, u in offline.page_tests(current_user.id, topic_id).items()}
    return render_template("user/lesson_topic.html", lesson=lesson, pcts=pcts, testable=testable, pack=pack,
                           open_n=len(gate) if pack is not None else open_lessons(gate), gate=gate, pass_min=m.PASS_MIN,
                           rids=catalog.lesson_result_ids(current_user.id, topic_id),
                           all_passed=all(p is not None and p >= m.PASS_MIN for p in gate))


@bp.get("/reja")
def plan():
    if _sample("oylik"):
        return render_template("user/plan.html", **_sample_plan())
    p = _my_plan()
    return render_template("user/plan.html", plan=p.items, s=p.summary, excluded=p.excluded, test_types=m.TEST_TYPES,
                           mandatory=m.MANDATORY_TYPES, decide=m.lesson_decision, pass_min=m.PASS_MIN, solid_min=m.SOLID_MIN)


def _sample_plan():
    """/ekranlar uchun namunaviy reja (mock.LEARN_PLAN), xuddi servis shaklida."""
    import copy
    items = copy.deepcopy(m.LEARN_PLAN)
    if request.args.get("oylik"):
        cur = next(i for i, x in enumerate(items) if x.get("state") == "current")
        items.insert(cur + 1, dict(m.MONTHLY_DUE))
    from .test import SLUG_OF
    for t in items:
        if t["kind"] == "test":
            t["url"] = url_for("user.control", namuna=1) if t["type"] == "interim" else url_for("test.question", turi=SLUG_OF[t["type"]])
            continue
        t["url"] = url_for("user.lesson", holat="qayta")
        t["test_url"] = url_for("test.question", turi="mavzu")
        t["passed"] = sum(1 for x in t["lessons"] if x["pct"] is not None)
        for x in t["lessons"]:
            x.update(url=url_for("user.lesson"), test_url=url_for("test.question", turi="dars"), testable=True, has_blocks=True)
    return {"plan": items, "s": m.PLAN_SUMMARY, "excluded": [{"name": n, "pct": p} for n, p in m.PLAN_EXCLUDED],
            "test_types": m.TEST_TYPES, "mandatory": m.MANDATORY_TYPES, "decide": m.lesson_decision,
            "pass_min": m.PASS_MIN, "solid_min": m.SOLID_MIN}


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
    """Namunaviy dars (/ekranlar). Ishga tushirilganda — joriy mavzu darsiga yo'naltiradi."""
    from .test import is_dev
    if not is_dev():
        from flask import redirect
        p = _my_plan()
        return redirect(p.current["url"] if p.current else url_for("user.plan"))
    retry = request.args.get("holat") == "qayta"
    topic = next(t for t in m.LEARN_PLAN if t.get("state") == "current")
    # Qayta o'zlashtirish namunasi — barcha dars testlari topshirilgan mavzu
    pcts = [100, 86, 92, 100] if retry else [l["pct"] for l in topic["lessons"]]
    return render_template("user/lesson.html", retry=retry, audio=bool(request.args.get("audio")),
                           pcts=pcts, open_n=open_lessons(pcts),
                           all_passed=all(p is not None and p >= m.PASS_MIN for p in pcts))


@bp.post("/bildirishnomalar/oqildi")
def notifications_seen():
    from flask import jsonify
    from flask_login import current_user

    from ..services import notify
    notify.mark_seen(current_user)
    return jsonify(ok=True)


@bp.get("/tutor/yechim/<ref>")
def tutor_solution(ref):
    """«Yechimini ko'rish»: savol va yechimi AI tutor suhbatiga (JSON). ref — "<urinish uuid>:<tartib>"."""
    import uuid as uuidlib

    from flask import abort, jsonify
    from flask_login import current_user

    from ..services import solutions
    from . import test as vt
    found = None
    head, _sep, pos = ref.rpartition(":")
    if vt.is_dev() and head in ("natija", "sinov"):                  # /ekranlar namunalari
        r = vt.sample_solution(head, int(pos) if pos.isdigit() else -1)
        found = (r, None) if r else None
    else:
        try:
            found = solutions.for_attempt(current_user.id, uuidlib.UUID(head), int(pos))
        except ValueError:
            pass
    if found is None:
        abort(404, _("Savol topilmadi"))
    r, lesson = found
    url = url_for("user.lesson_topic", topic_id=lesson[0], _anchor=f"k{lesson[1]}") if lesson else None
    return jsonify(ok=True, ask=render_template("partials/solution_ask.html", r=r),
                   html=render_template("partials/solution.html", r=r, lesson_url=url))


@bp.get("/tutor")
def tutor():
    from .test import is_dev
    return render_template("user/tutor.html", topic=request.args.get("mavzu") or _current_topic_name(), sample=is_dev())


def _current_topic_name() -> str:
    from flask_login import current_user

    from ..extensions import db
    from ..models import Topic
    from ..services import test_builder as tb
    tid = tb.current_topic(current_user.id)
    return db.session.get(Topic, tid).title if tid else _("Umumiy")


def _tests_ctx(**extra):
    """«Testlar» sahifasi: yakunlanmagan urinishlar va majburiy testlar jadvali (o'quv rejadan)."""
    from flask_login import current_user

    from ..services import attempts as at
    from ..services import test_builder as tb
    from ..services.timefmt import day_month, now
    from .test import attempt_url, is_dev, type_names, weekly_open
    from .test import close_overdue
    close_overdue()
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

    from ..services import plan as pl
    today = now()
    p = _my_plan()
    schedule = pl.schedule(p)
    for i in schedule:
        i.setdefault("url", url_for("test.question", turi="mavzu", mavzu=i["topic_id"]) if i.get("topic_id") else None)
    sunday = weekly_open()
    return {"unfinished": unfinished, "test_types": m.TEST_TYPES, "info": m.TEST_TYPE_INFO, "sunday": sunday,
            "next_sunday": day_month(today + timedelta(days=(6 - today.weekday()) % 7 or 7)), "mandatory": tb.MANDATORY,
            "schedule": schedule,
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
    """Oraliq sinov oldidan: navbati kelgan uch mavzu. Navbat kelmagan bo'lsa — «Testlar»ga."""
    from flask import flash, redirect
    if _sample():
        names = ["Shart operatorlari", "Sikllar (for, while)", "Funksiyalar"]
    else:
        it = next((t for t in _my_plan().interims if t["state"] in ("due", "started")), None)
        if it is None:
            flash(_("Oraliq sinov navbati hali kelmagan"))
            return redirect(url_for("user.tests"))
        names = [t["name"] for t in it["topics"]]
    return render_template("user/control.html", names=names)


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
    # /ekranlar namunalaridagi (reja, dars) natija havolalari: id ≥ m.MOCK_RID
    from .test import is_dev
    r = next((x for x in m.RESULTS if x["id"] == rid), None)
    if not r or not is_dev():
        abort(404)
    from .test import SLUG_OF
    retry = url_for("test.exam") if r["type"] == "exam" else url_for("test.question", turi=SLUG_OF.get(r["type"], "mavzu"))
    return render_template("user/result_detail.html", r=r, questions=sample_review(), decision=m.DECISION,
                           test_types=m.TEST_TYPES, staged=r["type"] in m.STAGED_TYPES, retry=retry, sample=True)


@bp.get("/xatolar")
def errors():
    from flask_login import current_user

    from ..services import catalog
    items, total = catalog.error_items(current_user.id)
    return render_template("user/errors.html", recommended=_recommended(), items=items, total=total)


@bp.get("/eslatmalar")
def notes():
    seed = [{"id": i + 1, "topic": t, "title": "", "text": text, "code": src or "", "when": when}
            for i, (t, text, src, when) in enumerate(m.NOTES)]
    from ..services import catalog
    topics = list(dict.fromkeys([n["topic"] for n in seed] + [t["name"] for t in catalog.topic_titles()]))
    return render_template("user/notes.html", notes=seed, topics=topics, current_topic=_current_topic_name())


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
    return respond(errors=errors, template="user/notes.html", notes=[], topics=[], current_topic=_current_topic_name(),
                   redirect_to=url_for("user.notes"), message=_("Eslatma saqlandi"))
