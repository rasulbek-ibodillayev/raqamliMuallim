"""Ekspert paneli: kontent va uning sifati — ekspertning vazifalari.

- Savollar banki (bosh sahifa): bazadagi savollar, filtrlar, sahifalash; «Tekshiruv navbati» va «Savol qo'shish».
- Tekshiruv navbati: AI tuzgan (source=ai, status=review) savollar. Ekspert tahrirlab tasdiqlaydi yoki rad etadi.
- Savol muharriri: yangi savol yoki mavjudini tahrirlash (?id=), har tahrir yangi versiya.
- Mavzular va darslar: hozircha namunaviy muharrir (brauzerda saqlanadi) — keyingi qismda bazaga o'tadi.
- E'tirozlar: test natijalari bazaga o'tgach ulanadi.

Ekspert panelidagi atamalar: «Mavzu» = sections, «Dars» = topics, «Kichik mavzu» = subtopics.
Mantiq: app/services/question_bank.py.
"""
from flask import Blueprint, abort, redirect, render_template, request, url_for
from flask_babel import gettext as _
from flask_login import current_user

from .. import mock as m
from . import account
from ..forms import field, required, respond, validate
from ..services import question_bank as qb
from ..services.uploads import UploadError, save_image

bp = Blueprint("expert", __name__, url_prefix="/ekspert")

# Profil: shaxsiy ma'lumotlar, telefon/email, parol, maxfiy so'z (app/views/account.py)
account.register(bp, "expert")


@bp.context_processor
def _nav_counts():
    """Yon menyudagi «Savollar banki» yonida — tekshiruvni kutayotgan AI savollari soni (bazadan)."""
    from sqlalchemy import func, select

    from ..extensions import db
    from ..models import Question
    n = db.session.scalar(select(func.count()).select_from(Question)
                          .where(Question.source == "ai", Question.status == "review"))
    nav = dict(m.NAV)
    nav["expert"] = [(e, label, ic, (n or None) if e == "expert.questions" else count)
                     for e, label, ic, count in m.NAV["expert"]]
    return {"nav": nav}


def _ctx(**extra):
    return {"panel": "expert", "kinds": m.Q_KINDS, "formats": m.Q_FORMATS, "levels": m.Q_LEVELS,
            "content": qb.content_tree(), **extra}


def _page():
    try:
        return max(1, int(request.args.get("sahifa", 1)))
    except ValueError:
        return 1


def _lessons(tree, section_id: str):
    return next((s["lessons"] for s in tree if str(s["id"]) == section_id), None)


@bp.get("/")
def questions():
    f = qb.Filters.from_args(request.args)
    items, found, pages, page = qb.list_questions(f, _page())
    _, queue_n, _, _ = qb.list_questions(qb.Filters(), 1, source="ai", status="review")
    ctx = _ctx()
    return render_template("expert/questions.html", items=items, found=found, pages=pages, page=page, f=vars(f),
                           state=m.Q_STATE, queue_n=queue_n, short=qb.shortage(), min_ratio=qb.MIN_RATIO,
                           lessons=_lessons(ctx["content"], f.mavzu), **ctx)


@bp.get("/savollar")
def questions_old():
    return redirect(url_for("expert.questions"), 301)


@bp.get("/navbat")
def queue():
    f = qb.Filters.from_args(request.args)
    items, found, pages, page = qb.list_questions(f, _page(), source="ai", status="review")
    _, total, _, _ = qb.list_questions(qb.Filters(), 1, source="ai", status="review")
    ctx = _ctx()
    return render_template("expert/queue.html", items=items, page=page, pages=pages, total=total, found=found,
                           f={k: v for k, v in vars(f).items() if k in ("q", "mavzu", "dars", "daraja")},
                           lessons=_lessons(ctx["content"], f.mavzu), **ctx)


@bp.post("/navbat/<int:qid>")
def queue_decide(qid):
    """Tasdiqlash (tahrirlangan holda) — savol bankka qo'shiladi; rad etish — o'chiriladi (berilgan bo'lsa arxivlanadi)."""
    q = qb.get(qid)
    if q is None or q.source != "ai" or q.status != "review":
        return respond(errors={"text": _("Savol topilmadi yoki allaqachon ko‘rib chiqilgan")}, template="expert/queue.html",
                       items=[], page=1, pages=1, total=0, found=0, f={}, lessons=None, **_ctx())
    if field("action") == "reject":
        qb.reject(qid, current_user.id)
        return respond(redirect_to=url_for("expert.queue"), message=_("Savol rad etildi va o‘chirildi"))
    text = field("text") or q.text
    opts = [o.strip() for o in request.form.getlist("opt")]
    right = sorted({int(r) for r in request.form.getlist("right") if r.isdigit()})
    data, answer = dict(q.data or {}), dict(q.answer or {})
    errors = {}
    if q.type in ("single", "multiple") and opts:
        keep = [i for i, o in enumerate(opts) if o]
        if len(keep) < 2:
            errors = {"opt": _("Kamida 2 ta javob varianti bo‘lsin")}
        keys = [keep.index(i) for i in right if i in keep]
        if not errors and not keys:
            errors = {"opt": _("To‘g‘ri javobni belgilang")}
        data["options"], answer["keys"] = [opts[i] for i in keep], keys
    elif q.type == "open" and opts and opts[0]:
        answer["value"] = opts[0]
    if not errors:
        try:
            qb.save({**qb._snapshot(q), "text": text, "data": data, "answer": answer}, current_user.id, qid)
        except qb.FormError as e:
            errors = {"opt" if k != "text" else "text": v for k, v in e.errors.items()}
    return respond(errors=errors, template="expert/queue.html", items=[], page=1, pages=1, total=0, found=0, f={},
                   lessons=None, **_ctx(),
                   redirect_to=url_for("expert.queue"), message=_("Savol tasdiqlandi va savollar bankiga qo‘shildi"))


# ---------- Savol muharriri ----------

def _init_from_question(q) -> dict:
    """Mavjud savol → muharrir boshlang'ich holati."""
    from ..models import Subtopic, Topic
    from ..extensions import db
    sub = db.session.get(Subtopic, q.subtopic_id)
    topic = db.session.get(Topic, sub.topic_id)
    d, a = q.data or {}, q.answer or {}
    init = {"id": q.id, "topic": str(topic.section_id), "lesson": str(topic.id), "subtopic": str(sub.id),
            "level": qb.DIFF_TO_LEVEL[q.difficulty], "kind": qb.TYPE_TO_KIND[q.type], "fmt": d.get("format", "matn"),
            "text": q.text, "why": q.explanation or "", "time": q.time_limit_s or 60,
            "opts": d.get("options") or ["", "", "", ""], "right": a.get("keys") or [0],
            "pairs": [[l, d.get("right", [])[r]] for l, r in zip(d.get("left", []), a.get("pairs", []))] or [["", ""]] * 3,
            "answer": a.get("value", ""), "answer_alt": ", ".join(a.get("accept", [])),
            "diagram": d.get("diagram", ""), "image": (d.get("image") or {}).get("src", ""),
            "image_alt": (d.get("image") or {}).get("alt", ""), "table": (d.get("table") or {}).get("rows", [])}
    return init


def _init_from_form() -> dict:
    """Xato bilan qaytgan forma — kiritilganlar saqlanadi."""
    g = request.form.getlist
    return {"id": field("id"), "topic": field("topic"), "lesson": field("lesson"), "subtopic": field("subtopic"),
            "level": field("level") or "O‘rta", "kind": field("kind") or "yopiq", "fmt": field("format") or "matn",
            "text": field("text"), "why": field("why"), "time": field("time") or 60,
            "opts": g("opt") or ["", "", "", ""], "right": [int(r) for r in g("right") if r.isdigit()] or [0],
            "pairs": [list(p) for p in zip(g("left"), g("right_txt"))] or [["", ""]] * 3,
            "answer": field("answer"), "answer_alt": field("answer_alt"), "diagram": field("diagram"),
            "image": field("image_keep"), "image_alt": field("image_alt"), "table": []}


def _payload(existing=None) -> tuple[dict | None, dict]:
    """Forma → savol (question_bank.save uchun) yoki xatolar."""
    kind, level, fmt = field("kind"), field("level"), field("format")
    tree = qb.content_tree()
    lessons = _lessons(tree, field("topic")) or []
    subs = next((l["subtopics"] for l in lessons if str(l["id"]) == field("lesson")), [])
    errors = validate({
        "topic": (field("topic"), lambda v: None if lessons else _("Mavzuni tanlang")),
        "lesson": (field("lesson"), lambda v: None if subs else _("Darsni tanlang")),
        "subtopic": (field("subtopic"), lambda v: None if any(str(s["id"]) == v for s in subs) else _("Kichik mavzuni tanlang")),
        "level": (level, lambda v: None if v in qb.LEVEL_TO_DIFF else _("Qiyinlik darajasini tanlang")),
        "kind": (kind, lambda v: None if v in qb.KIND_TO_TYPE else _("Savol turini tanlang")),
        "format": (fmt, lambda v: None if v in m.Q_FORMATS else _("Savol formatini tanlang")),
        "time": (field("time"), lambda v: None if v.isdigit() and 10 <= int(v) <= 1800 else _("Vaqt 10–1800 soniya oralig‘ida bo‘lsin")),
        "text": (field("text"), lambda v: required(v, _("Savol matnini kiriting"))),
    })
    if errors:
        return None, errors
    data, answer = {"format": fmt}, {}
    g = request.form.getlist
    if kind == "ochiq":
        if not field("answer"):
            return None, {"answer": _("To‘g‘ri javobni kiriting")}
        answer = {"value": field("answer")}
        alt = [x.strip() for x in field("answer_alt").split(",") if x.strip()]
        if alt:
            answer["accept"] = alt
    elif kind == "moslash":
        pairs = [(a.strip(), b.strip()) for a, b in zip(g("left"), g("right_txt")) if a.strip() and b.strip()]
        if len(pairs) < 2:
            return None, {"pairs": _("Kamida 2 ta to‘liq juftlik kiriting")}
        data.update(left=[a for a, _b in pairs], right=[b for _a, b in pairs])
        answer = {"pairs": list(range(len(pairs)))}   # testda o'ng ustun aralashtirib beriladi
    else:
        opts = [o.strip() for o in g("opt")]
        keep = [i for i, o in enumerate(opts) if o]
        marks = [int(r) for r in g("right") if r.isdigit() and int(r) in keep]
        if len(keep) < 2:
            return None, {"opt": _("Kamida 2 ta javob varianti bo‘lsin")}
        if not marks:
            return None, {"opt": _("To‘g‘ri javobni belgilang")}
        if kind == "kop" and len(marks) < 2:
            return None, {"opt": _("Ko‘p javobli savolda kamida 2 ta to‘g‘ri javob bo‘lsin")}
        if kind == "yopiq" and len(marks) != 1:
            return None, {"opt": _("Bitta to‘g‘ri javobni belgilang")}
        data["options"] = [opts[i] for i in keep]
        answer = {"keys": sorted(keep.index(i) for i in marks)}
    # Format qo'shimchalari
    try:
        if fmt == "rasm":
            src = save_image(request.files.get("image")) or field("image_keep")
            if not src:
                return None, {"text": _("Rasmni yuklang")}
            data["image"] = {"src": src, "alt": field("image_alt")}
        elif fmt == "chizma":
            src = save_image(request.files.get("diagram_file"))
            if src:
                data["image"] = {"src": src, "alt": field("image_alt") or _("Chizma")}
            elif field("diagram"):
                data["diagram"] = field("diagram")[:5000]
            elif field("image_keep"):
                data["image"] = {"src": field("image_keep"), "alt": field("image_alt") or _("Chizma")}
            else:
                return None, {"text": _("Chizma matnini kiriting yoki rasmini yuklang")}
        elif fmt == "jadval":
            try:
                rows_n, cols_n = min(10, int(field("rows") or 0)), min(8, int(field("cols") or 0))
            except ValueError:
                rows_n = cols_n = 0
            rows = [[field(f"cell_{r}_{c}")[:200] for c in range(1, cols_n + 1)] for r in range(1, rows_n + 1)]
            rows = [r for r in rows if any(r)]
            if not rows:
                return None, {"text": _("Jadvalni to‘ldiring")}
            data["table"] = {"rows": rows}
    except UploadError as e:
        return None, {"text": str(e)}
    payload = {"subtopic_id": int(field("subtopic")), "type": qb.KIND_TO_TYPE[kind], "difficulty": qb.LEVEL_TO_DIFF[level],
               "text": field("text")[:3000], "data": data, "answer": answer, "explanation": field("why")[:2000] or None,
               "time_limit_s": int(field("time"))}
    return payload, {}


@bp.get("/savol")
def editor():
    qid = request.args.get("id", type=int)
    init = None
    if qid:
        q = qb.get(qid)
        if q is None or q.status == "archived":
            abort(404)
        init = _init_from_question(q)
    return render_template("expert/editor.html", init=init, **_ctx())


@bp.post("/savol")
def editor_save():
    """Yangi savol yoki tahrir (id maydoni). Turi bo'yicha javoblar: yopiq — bitta to'g'ri; ko'p javobli —
    bir nechta to'g'ri; moslashtirish — juftliklar; ochiq — to'g'ri javob matni (va boshqa yozilishlar)."""
    qid = int(field("id")) if field("id").isdigit() else None
    if qid and qb.get(qid) is None:
        abort(404)
    payload, errors = _payload()
    if not errors:
        try:
            qb.save(payload, current_user.id, qid)
        except qb.FormError as e:
            errors = e.errors
    return respond(errors=errors, template="expert/editor.html", init=_init_from_form(), **_ctx(),
                   redirect_to=url_for("expert.questions"),
                   message=_("Savol yangilandi") if qid else _("Savol saqlandi va savollar bankiga qo‘shildi"))


@bp.post("/savollar/<int:qid>/ochirish")
def question_delete(qid):
    """«O'chirish» — arxivlash: savol testlarga tushmaydi, o'tgan natijalar va versiyalar saqlanadi."""
    if not qb.archive(qid, current_user.id):
        return respond(errors={"id": _("Savol topilmadi")}, template="expert/questions.html", items=[], found=0, pages=1,
                       page=1, f={}, state=m.Q_STATE, queue_n=0, short=[], min_ratio=qb.MIN_RATIO, lessons=None, **_ctx())
    return respond(redirect_to=url_for("expert.questions"), message=_("Savol o‘chirildi"))


@bp.get("/mavzular")
def topics():
    # Hozircha namunaviy muharrir (brauzerda saqlanadi); bazaga keyingi qismda o'tadi
    return render_template("expert/topics.html", block_kinds=[(k, i, str(l)) for k, i, l in m.BLOCK_KINDS],
                           **{**_ctx(), "content": m.EXPERT_CONTENT})


@bp.get("/etirozlar")
def objections():
    return render_template("expert/objections.html", items=m.EXPERT_OBJ, panel="expert")
