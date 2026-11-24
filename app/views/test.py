"""Testlar: boshlash, pleyer, bosqichlar orasi va natija (bazadan).

  /test/savol?turi=…            → yakunlanmagani bo'lsa davom ettiradi, aks holda yangi urinish → /test/urinish/<uuid>
  /test/sinov                   → attestatsiya testi (xuddi shunday)
  /test/urinish/<uuid>          pleyer: joriy bosqichning hamma savollari bitta sahifada (oflayn ham ishlaydi)
  /test/urinish/<uuid>/bosqich  bosqichlar orasi
  /test/urinish/<uuid>/natija   natija va tahlil

/test/savol?tur=…, /test/sinov?namuna=1, /test/bosqich, /test/natija, /test/sinov/natija — /ekranlar uchun namunaviy
ekranlar: bazaga tegmaydi va faqat ishlab chiqishda ochiladi (aks holda «Testlar»ga yo'naltiriladi).
"""
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_babel import gettext as _
from flask_login import current_user

from .. import mock as m
from ..services import attempts as at
from ..services import objections as ob
from ..services import scoring
from ..services import test_builder as tb

# Test turi URL'da (?turi=…) → urinish turi (mock.TEST_TYPES kaliti). «Bosqichlar orasi» ekrani faqat tb.STAGED uchun.
TYPE_SLUGS = {"diagnostika": "diagnostic", "mavzu": "topic", "kunlik": "daily", "oraliq": "interim", "haftalik": "weekly",
              "ixtiyoriy": "optional", "oylik": "monthly", "yakuniy": "final", "xatolar": "errors",
              "dars": "lesson"}
SLUG_OF = {v: k for k, v in TYPE_SLUGS.items()}


def _test_type():
    t = request.args.get("turi") or ("xatolar" if request.args.get("manba") == "xatolar" else "mavzu")
    return TYPE_SLUGS.get(t, "topic"), (t if t in TYPE_SLUGS else "mavzu")


bp = Blueprint("test", __name__, url_prefix="/test")


def is_dev() -> bool:
    return bool(current_app.debug or current_app.config.get("DEV_TOOLS"))


# ---------------- Haqiqiy testlar ----------------

def attempt_url(a) -> str:
    """Urinishning hozirgi holatiga mos sahifa."""
    if a.status == "submitted":
        return url_for("test.attempt_result", attempt_uuid=a.client_uuid)
    if a.status == "in_progress" and at.is_staged(a) and a.stage > 1:
        return url_for("test.attempt_stage", attempt_uuid=a.client_uuid)
    return url_for("test.attempt", attempt_uuid=a.client_uuid)


def _own(attempt_uuid):
    a = at.get(attempt_uuid)
    if a is None or a.user_id != current_user.id or a.status == "abandoned":
        abort(404)
    return a


def _start(kind, **params):
    try:
        a, fresh = tb.get_or_start(current_user.id, kind, **params)
    except tb.Unavailable as e:
        flash(str(e))
        return redirect(url_for("user.tests"))
    if not fresh and kind in ("optional", "errors"):
        flash(_("Yakunlanmagan testingiz davom ettirilmoqda"))
    return redirect(attempt_url(a))


@bp.get("/savol")
def question():
    if "tur" in request.args or "oflayn" in request.args:
        return _sample_question() if is_dev() else redirect(url_for("user.tests"))
    kind, _slug = _test_type()
    if kind == "weekly" and not weekly_open():
        flash(_("Haftalik test faqat yakshanba kuni ochiladi"))
        return redirect(url_for("user.tests"))
    n = request.args.get("soni", type=int)
    params = {}
    if kind == "topic":
        params["topic_id"] = request.args.get("mavzu", type=int)
    elif kind == "lesson":
        params["subtopic_id"] = request.args.get("dars", type=int)
    elif kind in ("optional", "errors"):
        params["n"] = max(5, min(30, n)) if n else None
        if kind == "optional":
            params["topic_ids"] = request.args.getlist("mavzu", type=int)
    return _start(kind, **params)


def weekly_open() -> bool:
    """Haftalik test faqat yakshanba ochiq. Ishlab chiqishda ?kun=yakshanba / ?kun=boshqa bilan sinash mumkin."""
    from ..services.timefmt import now
    day = request.args.get("kun") if is_dev() else None
    return day == "yakshanba" or (now().weekday() == 6 and day != "boshqa")


@bp.get("/urinish/<uuid:attempt_uuid>")
def attempt(attempt_uuid):
    a = _own(attempt_uuid)
    if a.status != "in_progress":
        return redirect(attempt_url(a))
    qs = at.play_view(a)
    cfg = {"uuid": str(a.client_uuid), "kind": a.kind, "stage": a.stage, "answers": at.saved_answers(a),
           "duration": a.settings_snapshot.get("seconds"), "sample": False}
    sent = ob.sent_positions(a)
    for q in qs:
        q["ref"], q["objected"] = ob.ref(a, q["pos"]), q["pos"] in sent
    if a.kind == "exam":
        return _render_exam(qs, {**cfg, "cur": None, "seed": {}, "confirm": False,
                                 "resultUrl": url_for("test.attempt_result", attempt_uuid=a.client_uuid)})
    stages = at.stages(a)
    label = f"{_('%(n)s-bosqich', n=a.stage)} · {at.LEVELS[stages[a.stage - 1]['level']]}" if stages else ""
    return _render_player(qs, cfg, name=at.names([a], type_names())[a.id], stage_label=label)


@bp.get("/urinish/<uuid:attempt_uuid>/bosqich")
def attempt_stage(attempt_uuid):
    a = _own(attempt_uuid)
    if a.status != "in_progress" or not at.is_staged(a) or a.stage < 2:
        return redirect(url_for("test.attempt", attempt_uuid=a.client_uuid))
    stages, skipped = at.stages(a), set(a.settings_snapshot.get("skipped", []))
    # Oxirgi baholangan bosqich: oradagi bosqichlar butunlay o'tkazib yuborilgan bo'lishi mumkin
    prev = next(i for i in range(a.stage - 1, 0, -1)
                if any(p not in skipped for p in range(stages[i - 1]["from"], stages[i - 1]["to"])))
    scores = [i.score or 0 for i in a.items
              if stages[prev - 1]["from"] <= i.position < stages[prev - 1]["to"] and i.position not in skipped]
    return render_template("test/stage.html", tname=at.names([a], type_names())[a.id], pct=scoring.percent(scores),
                           done=prev, stage=a.stage, levels=[at.LEVELS[s["level"]] for s in stages],
                           n=len(at.active_positions(a)), minutes=-(-a.settings_snapshot["seconds"] // 60),
                           advice=at.advice(a), pass_min=scoring.PASS_MIN,
                           next_url=url_for("test.attempt", attempt_uuid=a.client_uuid))


@bp.get("/urinish/<uuid:attempt_uuid>/natija")
def attempt_result(attempt_uuid):
    a = _own(attempt_uuid)
    if a.status != "submitted":
        return redirect(url_for("test.attempt", attempt_uuid=a.client_uuid))
    if a.kind == "diagnostic":
        return redirect(url_for("user.diagnostic_result"))
    qs = review_of(a)
    if a.kind == "exam":
        return _render_exam_result(qs, at.by_subtopic(a), a.total, int(a.score_pct))
    return render_template("test/result.html", r=summary(a), questions=qs, by_sub=at.by_subtopic(a),
                           advice=at.advice(a) if at.is_staged(a) else None)


def type_names():
    return {k: v[0] for k, v in m.TEST_TYPES.items()}


def review_of(a) -> list[dict]:
    qs, sent = at.review(a), ob.sent_positions(a)
    for q in qs:
        q["ref"], q["objected"] = ob.ref(a, q["pos"]), q["pos"] in sent
    return qs


def summary(a) -> dict:
    """Natija sarlavhasi va keyingi qadam."""
    return {"pct": int(a.score_pct), "decision": a.decision, "kind": a.kind, "name": at.names([a], type_names())[a.id],
            "topic_id": a.topic_id, "total": a.total, "retry": retry_url(a), "lesson_url": _lesson_url(a)}


def _lesson_url(a) -> str:
    """Natijadan keyin darsga: yiqilgan bo'lsa — shu darsning o'ziga, aks holda mavzu darsiga (darsi bo'lmasa — mavzuga)."""
    from ..services import catalog
    if not a.topic_id:
        return url_for("user.plan")
    lesson = catalog.lesson_view(a.topic_id)
    if not lesson or not lesson["parts"]:
        return url_for("user.topic", topic_id=a.topic_id)
    ids = [p["id"] for p in lesson["parts"]]
    anchor = None
    if a.subtopic_id in ids:
        k = ids.index(a.subtopic_id)
        anchor = f"k{ids[k if a.decision == 'fail' else min(k + 1, len(ids) - 1)]}"
    return url_for("user.lesson_topic", topic_id=a.topic_id, _anchor=anchor)


def retry_url(a) -> str:
    """Xuddi shu turdagi yangi test (yangi savollar bilan)."""
    if a.kind == "exam":
        return url_for("test.exam")
    args = {"turi": SLUG_OF[a.kind]}
    if a.kind == "lesson":
        args["dars"] = a.subtopic_id
    elif a.kind == "topic":
        args["mavzu"] = a.topic_id
    elif a.kind in ("optional", "errors"):
        args["soni"] = a.total
        if a.settings_snapshot.get("topic_ids"):
            args["mavzu"] = a.settings_snapshot["topic_ids"]
    return url_for("test.question", **args)


def _render_player(qs, cfg, *, name, stage_label, next_url=None, offline=False):
    cfg = {**cfg, "id": f"{cfg['uuid']}:{cfg['stage'] or 0}" if cfg.get("uuid") else "namuna",
           "nextUrl": next_url, "offline": offline,
           "questions": [{"pos": q["pos"], "mode": q["kind"]} for q in qs]}
    return render_template("test/question.html", qs=qs, cfg=cfg, tname=name, stage_label=stage_label, offline=offline)


def _render_exam(qs, state):
    """Attestatsiya oynasi: savollar JS'ga beriladi — to'g'ri javobsiz."""
    out = []
    for q in qs:
        img = q.get("image")
        out.append({"pos": q["pos"], "ref": q["ref"], "objected": q.get("objected", False), "topic": q["topic"],
                    "text": q["text"], "code": q.get("code"), "table": q.get("table"), "options": q["options"],
                    "image": {**img, "src": url_for("static", filename=img["src"])} if img else None})
    return render_template("test/exam.html", questions=out, state=state)


def _render_exam_result(qs, by_topic, total, pct):
    correct = sum(1 for q in qs if q["score"] == 100)
    blank = sum(1 for q in qs if not q["answered"])
    return render_template("test/exam_result.html", questions=qs, correct=correct, blank=blank, total=total, pct=pct,
                           by_topic=by_topic, pass_min=m.PASS_MIN, solid_min=m.SOLID_MIN)


# ---------------- Namunaviy ekranlar (/ekranlar) ----------------

QUESTIONS = {
    "yopiq": {"n": 4, "topic": "Shart operatorlari", "type": "Bitta javob",
              "text": "Quyidagi kod natijasini aniqlang:",
              "code": "x = 5\nif x > 3:\n    print(x * 2)",
              "options": ["5", "10", "15", "Xato beradi"]},
    "kop": {"n": 5, "topic": "Kompyuter qurilmalari", "type": "Bir nechta javob",
            "text": "Quyidagilardan qaysilari kiritish qurilmalari?",
            "options": ["Klaviatura", "Monitor", "Sichqoncha", "Printer", "Skaner"]},
    "moslash": {"n": 6, "topic": "Tarmoq texnologiyalari", "type": "Moslashtirish",
                "text": "Atamalarni ta’riflari bilan moslashtiring.",
                "pairs": ["HTTP", "DNS", "IP", "FTP"],
                "answers": ["Gipermatn uzatish protokoli", "Domen nomini IP-manzilga o‘giradi",
                            "Qurilmaning tarmoqdagi manzili", "Fayl uzatish protokoli"]},
    # Jadvalli savol (masalan, elektron jadval yoki rostlik jadvali bilan)
    "jadval": {"n": 8, "topic": "Elektron jadvallar", "type": "Bitta javob", "mode": "yopiq",
               "text": "Jadvalda C4 katakka =SUMIF(A1:A3;\">1\";B1:B3) formulasi yozildi. C4 qiymati nechaga teng?",
               "table": {"head": ["", "A", "B", "C"],
                         "rows": [["1", "1", "10", ""], ["2", "2", "20", ""], ["3", "3", "30", ""], ["4", "", "", "?"]]},
               "options": ["60", "50", "30", "20"]},
    # Rasmli savol (sxema, diagramma, ekran tasviri va h.k.)
    "rasm": {"n": 9, "topic": "Mantiq asoslari", "type": "Bitta javob", "mode": "yopiq",
             "text": "Rasmdagi mantiqiy sxema qaysi ifodaga mos keladi?",
             "image": {"src": "img/savol-mantiqiy-sxema.svg",
                       "alt": "Mantiqiy sxema: A va B kirishlari OR elementiga va AND elementiga ulangan; AND chiqishi NOT orqali o‘tadi; ikkala natija oxirgi AND elementiga beriladi, chiqish F.",
                       "caption": "1-rasm. Mantiqiy sxema"},
             "options": ["F = (A ∨ B) ∧ ¬(A ∧ B)", "F = (A ∧ B) ∨ ¬(A ∨ B)", "F = ¬(A ∨ B)", "F = A ∧ B"]},
    "ochiq": {"n": 7, "topic": "Sanoq sistemalari", "type": "Ochiq javob",
              "text": "101101₂ sonini o‘nlik sanoq sistemasiga o‘tkazing.",
              "numeric": True},
}


def _sample_question():
    kind = request.args.get("tur", "yopiq")
    kind = kind if kind in QUESTIONS else "yopiq"
    q = {**QUESTIONS[kind]}
    ttype, slug = _test_type()
    staged = ttype in m.STAGED_TYPES
    q.update(pos=0, kind=q.get("mode", kind), ref="namuna:0", objected=False)
    if "pairs" in q:
        q["answers"] = list(enumerate(q["answers"]))
    next_url = url_for("test.stage", turi=slug) if staged else url_for("test.result", turi=slug)
    return _render_player([q], {"uuid": None, "kind": ttype, "stage": None, "answers": {}, "duration": 600, "sample": True},
                          name=m.TEST_TYPES[ttype][0], stage_label=_("1-bosqich · Oson") if staged else "",
                          next_url=next_url, offline=bool(request.args.get("oflayn")))


def _to_tests():
    return redirect(url_for("user.tests"))


@bp.get("/bosqich")
def stage():
    """Namuna: bosqichlar orasi."""
    if not is_dev():
        return _to_tests()
    ttype, slug = _test_type()
    if request.args.get("turi") and ttype not in m.STAGED_TYPES:
        return redirect(url_for("test.result", turi=slug))
    if ttype not in m.STAGED_TYPES:
        ttype, slug = "interim", "oraliq"
    return render_template("test/stage.html", tname=m.TEST_TYPES[ttype][0], pct=90, done=1, stage=2,
                           levels=[at.LEVELS[d] for d in tb.DIFFICULTIES], n=10, minutes=15,
                           advice={"relearn": ["Tarmoq protokollari"],
                                   "lessons": [{"name": "if / else", "topic": "Python: shart operatorlari", "pct": 75}]},
                           pass_min=m.PASS_MIN, next_url=url_for("test.question", tur="kop", turi=slug))


def sample_review() -> list[dict]:
    """mock.RESULT_QUESTIONS → services.attempts.review shakli."""
    return [{**q, "kind": "yopiq", "score": 100 if q["mine"] == q["right"] else 0, "answered": q["mine"] is not None,
             "mine": [] if q["mine"] is None else [q["mine"]], "right": [q["right"]], "ref": f"namuna:{q['n']}",
             "objected": False} for q in m.RESULT_QUESTIONS]


@bp.get("/natija")
def result():
    """Namuna: natija."""
    if not is_dev():
        return _to_tests()
    failed = request.args.get("holat") == "qaytarildi"
    r = {"pct": 62 if failed else 78, "decision": "fail" if failed else "warn", "kind": "topic", "topic_id": None,
         "name": "Mavzu testi: Shart operatorlari", "total": 6, "retry": url_for("test.question", turi="mavzu"), "lesson_url": url_for("user.lesson", holat="qayta")}
    return render_template("test/result.html", r=r, questions=sample_review(),
                           by_sub=[("Kompyuter qurilmalari", 65, 1.3, 2), ("Shart operatorlari", 78, 1.6, 2),
                                   ("Sanoq sistemalari", 85, 1.7, 2)])


EXAM_POOL = [
    {"topic": "Mantiq asoslari", "text": "(A ∨ B) ∧ ¬(A ∧ B) mantiqiy ifodasi qachon 1 ga teng bo‘ladi?",
     "options": ["Faqat A va B bir vaqtda rost bo‘lganda", "A va B turli qiymatga ega bo‘lganda",
                 "A va B ikkalasi yolg‘on bo‘lganda", "Har doim"], "right": 1},
    {"topic": "Sanoq sistemalari", "text": "101101₂ sonini o‘nlik sanoq sistemasiga o‘tkazing.",
     "options": ["43", "45", "47", "53"], "right": 1},
    {"topic": "Dasturlash", "text": "Quyidagi Python kodi natijasini aniqlang:",
     "code": "s = 0\nfor i in range(1, 5):\n    s += i\nprint(s)", "options": ["10", "15", "4", "5"], "right": 0},
    {"topic": "Tarmoq texnologiyalari", "text": "DNS serverning asosiy vazifasi qaysi?",
     "options": ["Fayllarni uzatish", "Domen nomini IP-manzilga o‘girish", "Elektron xat yuborish", "Sahifani shifrlash"], "right": 1},
    {"topic": "Elektron jadvallar", "text": "C4 katakka =SUMIF(A1:A3;\">1\";B1:B3) formulasi yozildi. C4 qiymati nechaga teng?",
     "table": {"head": ["", "A", "B", "C"], "rows": [["1", "1", "10", ""], ["2", "2", "20", ""], ["3", "3", "30", ""], ["4", "", "", "?"]]},
     "options": ["60", "50", "30", "20"], "right": 1},
    {"topic": "Mantiq asoslari", "text": "Rasmdagi mantiqiy sxema qaysi ifodaga mos keladi?",
     "image": {"src": "img/savol-mantiqiy-sxema.svg", "alt": "Mantiqiy sxema: OR va NAND elementlari natijasi AND orqali F chiqishiga beriladi"},
     "options": ["F = (A ∨ B) ∧ ¬(A ∧ B)", "F = (A ∧ B) ∨ ¬(A ∨ B)", "F = ¬(A ∨ B)", "F = A ∧ B"], "right": 0},
    {"topic": "Axborot hajmi", "text": "256 xil belgidan iborat alifbodagi bitta belgi necha bit axborot olib keladi?",
     "options": ["6", "7", "8", "16"], "right": 2},
    # Rasmli savollar (attestatsiyada sxema, tarmoq chizmasi, blok-sxema va h.k. bo'ladi)
    {"topic": "Tarmoq texnologiyalari", "text": "Rasmda kompyuter tarmog‘ining qaysi topologiyasi tasvirlangan?",
     "image": {"src": "img/savol-tarmoq-topologiya.svg", "alt": "Oltita kompyuter markazdagi bitta hub qurilmasiga alohida kabel bilan ulangan"},
     "options": ["Shina", "Halqa", "Yulduz", "To‘liq bog‘langan"], "right": 2},
    {"topic": "Algoritmlash", "text": "Blok-sxemada tasvirlangan algoritm bajarilgach, qanday qiymat chiqariladi?",
     "image": {"src": "img/savol-blok-sxema.svg", "alt": "Blok-sxema: s = 0, i = 1; i ≤ 4 bo‘lsa s = s + i va i = i + 1, aks holda s chiqariladi"},
     "options": ["4", "6", "10", "15"], "right": 2},
]


def _pool_question(i):
    return {**EXAM_POOL[i % len(EXAM_POOL)], "pos": i, "ref": f"namuna:{i}", "objected": False}


@bp.get("/sinov")
def exam():
    """Attestatsiya testi. ?namuna=1 — /ekranlar uchun: oldindan javob berilgan, serverga yuborilmaydigan sessiya."""
    if "namuna" not in request.args or not is_dev():
        return _start("exam")
    qs = [_pool_question(i) for i in range(35)]
    start_given = "savol" in request.args
    start = max(1, min(35, request.args.get("savol", 1, type=int) or 1)) - 1
    return _render_exam(qs, {"uuid": None, "kind": "exam", "stage": None, "answers": {}, "duration": tb.EXAM_SECONDS,
                             "sample": True, "cur": start if start_given else None,
                             "seed": {i: (i * 3) % 4 for i in range(1, 11) if i != start},
                             "confirm": bool(request.args.get("yakun")), "resultUrl": url_for("test.exam_result")})


@bp.get("/sinov/natija")
def exam_result():
    """Namuna: attestatsiya testi yakuni."""
    if not is_dev():
        return _to_tests()
    qs, acc = [], {}
    for i in range(35):
        q = _pool_question(i)
        right = q["right"]
        # namuna: har 4-savol xato, 33–35 javobsiz; «Mantiq asoslari»da xato ko'proq
        if i >= 32:
            mine = []
        elif i % 4 == 3 or (q["topic"] == "Mantiq asoslari" and i % 3 == 0):
            mine = [(right + 1) % len(q["options"])]
        else:
            mine = [right]
        score = 100 if mine == [right] else 0
        acc.setdefault(q["topic"], []).append(score)
        qs.append({**q, "n": i + 1, "q": q["text"], "kind": "yopiq", "mine": mine, "right": [right], "score": score,
                   "answered": bool(mine)})
    by_topic = sorted(((name, scoring.percent(s), sum(s) // 100, len(s)) for name, s in acc.items()), key=lambda x: x[1])
    return _render_exam_result(qs, by_topic, 35, scoring.percent([q["score"] for q in qs]))
