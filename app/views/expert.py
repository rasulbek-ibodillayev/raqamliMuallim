"""Ekspert paneli: kontent va uning sifati — ekspertning vazifalari.

- Savollar banki (bosh sahifa): bazadagi savollar, filtrlar, sahifalash; «Tekshiruv navbati» va «Savol qo'shish».
- Tekshiruv navbati: AI tuzgan (source=ai, status=review) savollar. Ekspert tahrirlab tasdiqlaydi yoki rad etadi.
- Savol muharriri: yangi savol yoki mavjudini tahrirlash (?id=), har tahrir yangi versiya.
- Mavzular va darslar: mavzu, dars, kichik mavzu, bloklar va shablonlar (services/content_editor.py).
- E'tirozlar: savol bo'yicha ko'rib chiqish, natijalarni qayta hisoblash (services/objection_review.py, recalc.py).

Huquqlar (services/experts.py): har amal uchun perms (_NEED), mavzular bo'yicha areas. Ko'rish — hammaga, o'z mavzularida.
Ekspert panelidagi atamalar: «Mavzu» = sections, «Dars» = topics, «Kichik mavzu» = subtopics.
"""
from flask import Blueprint, Response, abort, jsonify, redirect, render_template, request, url_for
from flask_babel import gettext as _
from flask_babel import lazy_gettext as _l
from flask_login import current_user

from .. import mock as m
from ..extensions import db
from . import account
from ..forms import field, required, respond, validate
from ..services import content_editor as ce
from ..services import experts
from ..services import objection_review as rv
from ..services import question_bank as qb
from ..services.question_templates import TEMPLATES
from ..services.uploads import UploadError, save_image

bp = Blueprint("expert", __name__, url_prefix="/ekspert")

# Profil: shaxsiy ma'lumotlar, telefon/email, parol, maxfiy so'z (app/views/account.py)
account.register(bp, "expert")


# Amal → kerakli huquq. Bu yerda yo'q sahifalar (savollar banki, profil) hamma ekspertga ochiq
_NEED = {"queue": "review", "queue_decide": "review", "editor": "questions", "editor_save": "questions",
         "excel_sample": "questions", "excel_import": "questions", "question_delete": "questions", "topics": "topics",
         "topics_api": "topics", "lesson_get": "topics", "lesson_save": "topics", "lesson_image": "topics",
         "objections": "objections", "objection_decide": "objections", "objection_pause": "objections"}


@bp.before_request
def _check_perm():
    need = _NEED.get((request.endpoint or "").removeprefix("expert."))
    if need and current_user.is_authenticated and current_user.role == "expert" and need not in experts.perms(current_user):
        abort(403)


@bp.context_processor
def _nav_counts():
    """Yon menyu: faqat ruxsat etilgan bo'limlar, yonida — kutayotgan AI savollari va e'tirozlar soni (bazadan)."""
    if not current_user.is_authenticated or current_user.role != "expert":
        return {}
    allowed, areas = experts.perms(current_user), experts.my_areas()
    _items, n, _pages, _p = qb.list_questions(qb.Filters(), 1, source="ai", status="review", areas=areas)
    counts = {"expert.questions": n, "expert.objections": rv.count(areas) if "objections" in allowed else 0}
    nav = dict(m.NAV)
    nav["expert"] = [(e, label, ic, counts.get(e) or None) for e, label, ic, _c in m.NAV["expert"]
                     if _NEED.get(e.removeprefix("expert."), "") in ("", *allowed)]
    return {"nav": nav, "can": allowed}


def _ctx(**extra):
    return {"panel": "expert", "kinds": m.Q_KINDS, "formats": m.Q_FORMATS, "levels": m.Q_LEVELS,
            "content": qb.content_tree(experts.my_areas()), **extra}


def _own_question(qid: int | None):
    """Savol — faqat o'z mavzularidan (boshqasi 403, yo'g'i None)."""
    q = qb.get(qid) if qid else None
    if q is not None:
        experts.require_section(experts.section_of_question(q.id))
    return q


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
    areas = experts.my_areas()
    items, found, pages, page = qb.list_questions(f, _page(), areas=areas)
    _, queue_n, _, _ = qb.list_questions(qb.Filters(), 1, source="ai", status="review", areas=areas)
    ctx = _ctx()
    return render_template("expert/questions.html", items=items, found=found, pages=pages, page=page, f=vars(f),
                           state=m.Q_STATE, queue_n=queue_n, short=qb.shortage(areas), min_ratio=qb.MIN_RATIO,
                           lessons=_lessons(ctx["content"], f.mavzu), **ctx)


@bp.get("/savollar")
def questions_old():
    return redirect(url_for("expert.questions"), 301)


@bp.get("/navbat")
def queue():
    f = qb.Filters.from_args(request.args)
    areas = experts.my_areas()
    items, found, pages, page = qb.list_questions(f, _page(), source="ai", status="review", areas=areas)
    _, total, _, _ = qb.list_questions(qb.Filters(), 1, source="ai", status="review", areas=areas)
    ctx = _ctx()
    return render_template("expert/queue.html", items=items, page=page, pages=pages, total=total, found=found,
                           f={k: v for k, v in vars(f).items() if k in ("q", "mavzu", "dars", "daraja")},
                           lessons=_lessons(ctx["content"], f.mavzu), **ctx)


@bp.post("/navbat/<int:qid>")
def queue_decide(qid):
    """Tasdiqlash (tahrirlangan holda) — savol bankka qo'shiladi; rad etish — o'chiriladi (berilgan bo'lsa arxivlanadi)."""
    q = _own_question(qid)
    if q is None or q.source != "ai" or q.status != "review":
        return respond(errors={"text": _("Savol topilmadi yoki allaqachon ko‘rib chiqilgan")}, template="expert/queue.html",
                       items=[], page=1, pages=1, total=0, found=0, f={}, lessons=None, **_ctx())
    if field("action") == "reject":
        qb.reject(qid, current_user.id)
        return respond(redirect_to=url_for("expert.queue"), message=_("Savol rad etildi"))
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

def _format_of(d: dict) -> str:
    """JSON'dan yuklangan savollarda format yozilmagan bo'ladi: qo'shimchasidan aniqlanadi (aks holda tahrirda yo'qolardi)."""
    if d.get("table"):
        return "jadval"
    if d.get("diagram"):
        return "chizma"
    if d.get("image"):
        return "chizma" if d.get("format") == "chizma" else "rasm"
    return "matn"


def _init_from_question(q) -> dict:
    """Mavjud savol → muharrir boshlang'ich holati."""
    from ..models import Subtopic, Topic
    sub = db.session.get(Subtopic, q.subtopic_id)
    topic = db.session.get(Topic, sub.topic_id)
    d, a = q.data or {}, q.answer or {}
    init = {"id": q.id, "topic": str(topic.section_id), "lesson": str(topic.id), "subtopic": str(sub.id),
            "level": qb.DIFF_TO_LEVEL[q.difficulty], "kind": qb.TYPE_TO_KIND[q.type], "fmt": _format_of(d),
            "text": q.text, "why": q.explanation or "", "time": q.time_limit_s or 60,
            "opts": d.get("options") or ["", "", "", ""], "right": a.get("keys") or [0],
            "notes": a.get("notes") or [""] * len(d.get("options") or [0] * 4), "code": d.get("code", ""),
            "pairs": [[l, d.get("right", [])[r]] for l, r in zip(d.get("left", []), a.get("pairs", []))] or [["", ""]] * 3,
            "answer": a.get("value", ""), "answer_alt": ", ".join(a.get("accept", [])),
            "diagram": d.get("diagram", ""), "image": (d.get("image") or {}).get("src", ""),
            "image_alt": (d.get("image") or {}).get("alt", ""), "table": ([d["table"]["head"]] if (d.get("table") or {}).get("head") else []) + (d.get("table") or {}).get("rows", []),
            "table_head": bool((d.get("table") or {}).get("head"))}
    return init


def _init_from_form() -> dict:
    """Xato bilan qaytgan forma — kiritilganlar saqlanadi."""
    g = request.form.getlist
    return {"id": field("id"), "topic": field("topic"), "lesson": field("lesson"), "subtopic": field("subtopic"),
            "level": field("level") or "O‘rta", "kind": field("kind") or "yopiq", "fmt": field("format") or "matn",
            "text": field("text"), "why": field("why"), "time": field("time") or 60,
            "opts": g("opt") or ["", "", "", ""], "right": [int(r) for r in g("right") if r.isdigit()] or [0],
            "notes": g("opt_note") or [""] * 4, "code": request.form.get("code", ""),
            "pairs": [list(p) for p in zip(g("left"), g("right_txt"))] or [["", ""]] * 3,
            "answer": field("answer"), "answer_alt": field("answer_alt"), "diagram": field("diagram"),
            "image": field("image_keep"), "image_alt": field("image_alt"), "table": _table_rows(), "table_head": bool(field("table_head"))}


def _table_rows() -> list[list[str]]:
    try:
        rows_n, cols_n = min(12, int(field("rows") or 0)), min(8, int(field("cols") or 0))
    except ValueError:
        return []
    rows = [[field(f"cell_{r}_{c}")[:200] for c in range(1, cols_n + 1)] for r in range(1, rows_n + 1)]
    return [r for r in rows if any(r)]


def _payload() -> tuple[dict | None, dict]:
    """Forma → savol (question_bank.save uchun) yoki xatolar."""
    kind, level, fmt = field("kind"), field("level"), field("format")
    tree = qb.content_tree(experts.my_areas())
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
    if field("code"):                                   # boshidagi bo'sh joylar ahamiyatli
        data["code"] = request.form["code"].replace("\r\n", "\n").strip("\n")[:5000]
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
        notes = [n.strip()[:500] for n in g("opt_note")]
        notes = [notes[i] if i < len(notes) else "" for i in keep]
        if any(notes):
            answer["notes"] = notes
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
            rows = _table_rows()
            if not rows:
                return None, {"text": _("Jadvalni to‘ldiring")}
            data["table"] = {"head": rows[0], "rows": rows[1:]} if field("table_head") and len(rows) > 1 else {"rows": rows}
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
        q = _own_question(qid)
        if q is None or q.status == "archived":
            abort(404)
        init = _init_from_question(q)
    return render_template("expert/editor.html", init=init, **_ctx())


@bp.post("/savol")
def editor_save():
    """Yangi savol yoki tahrir (id maydoni). Turi bo'yicha javoblar: yopiq — bitta to'g'ri; ko'p javobli —
    bir nechta to'g'ri; moslashtirish — juftliklar; ochiq — to'g'ri javob matni (va boshqa yozilishlar)."""
    qid = int(field("id")) if field("id").isdigit() else None
    if qid and _own_question(qid) is None:
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


@bp.get("/savol/namuna.xlsx")
def excel_sample():
    """Excel orqali savol qo'shish uchun namunaviy fayl (har bir savol turiga misol)."""
    return _xlsx(qb.excel_sample(), "savollar-namuna.xlsx")


def _xlsx(data: bytes, name: str):
    return Response(data, headers={"Content-Disposition": f'attachment; filename="{name}"', "Cache-Control": "no-store"},
                    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@bp.get("/savollar/eksport.xlsx")
def questions_export():
    """Filtrdagi savollar Excel'da (import formatida)."""
    return _xlsx(qb.export_excel(qb.Filters.from_args(request.args), experts.my_areas()), "savollar.xlsx")


@bp.post("/savol/excel")
def excel_import():
    """Excel fayldan savollar: yopiq, ko'p javobli, moslashtirish va ochiq (matnli). Fayl to'liq tekshiriladi —
    bitta qatorda xato bo'lsa ham hech narsa yozilmaydi."""
    f = request.files.get("file")
    if not f or not f.filename:
        errors = {"file": _("Excel faylni tanlang")}
    elif not f.filename.lower().endswith(".xlsx"):
        errors = {"file": _("Fayl .xlsx formatida bo‘lsin")}
    else:
        n, errs = qb.import_excel(f.read(), current_user.id, experts.my_areas())
        errors = {"file": "; ".join(errs)} if errs else {}
    return respond(errors=errors, template="expert/editor.html", init=None, **_ctx(),
                   redirect_to=url_for("expert.questions"),
                   message=_("%(n)s ta savol savollar bankiga qo‘shildi", n=n) if not errors else None)


@bp.post("/savollar/<int:qid>/ochirish")
def question_delete(qid):
    """«O'chirish» — arxivlash: savol testlarga tushmaydi, o'tgan natijalar va versiyalar saqlanadi."""
    if _own_question(qid) is None or not qb.archive(qid, current_user.id):
        return respond(errors={"id": _("Savol topilmadi")}, template="expert/questions.html", items=[], found=0, pages=1,
                       page=1, f={}, state=m.Q_STATE, queue_n=0, short=[], min_ratio=qb.MIN_RATIO, lessons=None, **_ctx())
    return respond(redirect_to=url_for("expert.questions"), message=_("Savol o‘chirildi"))


# ---------- Mavzular va darslar ----------

_BLOCKS = [("text", "note", _l("Matn")), ("code", "code", _l("Kod")), ("image", "image", _l("Rasm")), ("table", "table", _l("Jadval")),
           ("mermaid", "graph", _l("Chizma")), ("formula", "sigma", _l("Formula")), ("video", "play", _l("Video")),
           ("callout", "info", _l("Eslatma")), ("links", "link", _l("Havolalar"))]


@bp.get("/mavzular")
def topics():
    cfg = {"tree": ce.tree(experts.my_areas()), "kinds": [(k, ic, str(label)) for k, ic, label in _BLOCKS],
           "templates": [(t.name, t.title) for t in TEMPLATES.values()],
           "urls": {"api": url_for("expert.topics_api"), "lesson": url_for("expert.lesson_get", tid=0),
                    "image": url_for("expert.lesson_image"), "static": url_for("static", filename="")},
           "t": {"savedTopic": _("Mavzu saqlandi"), "savedLesson": _("Dars qo‘shildi"), "deleted": _("O‘chirildi"),
                 "saved": _("Dars saqlandi"), "unsaved": _("Saqlanmagan o‘zgarishlar yo‘qoladi. Davom etasizmi?"),
                 "hasQuestions": _("Bu kichik mavzuning savollari bor, o‘chirib bo‘lmaydi"),
                 "confirmSub": _("Kichik mavzu bloklari bilan o‘chirilsinmi?")}}
    return render_template("expert/topics.html", panel="expert", cfg=cfg)


def _json_errors(fn):
    """Muharrir xatolari → {"ok": false, "error"} (422; boshqa ekspert orada saqlagan bo'lsa 409)."""
    from functools import wraps

    @wraps(fn)
    def run(*a, **kw):
        try:
            return fn(*a, **kw)
        except (ce.EditError, UploadError) as e:
            db.session.rollback()
            return jsonify(ok=False, error=str(e)), 409 if isinstance(e, ce.Conflict) else 422
    return run


def _section_of_topic(tid) -> int | None:
    from ..models import Topic
    t = db.session.get(Topic, tid) if isinstance(tid, int) else None
    return t.section_id if t else None


@bp.post("/mavzular/api")
@_json_errors
def topics_api():
    """Daraxt amallari: section_save, section_delete, lesson_add, lesson_delete, move."""
    d = request.get_json(silent=True)
    d = d if isinstance(d, dict) else {}
    op, item = d.get("op"), d.get("id")
    item = item if isinstance(item, int) and not isinstance(item, bool) else None
    uid, new_id = current_user.id, None
    if op == "section_save":
        if item is None and experts.my_areas() is not None:
            abort(403)                                  # yangi mavzu — faqat hamma mavzuga huquqi bor ekspert
        if item is not None:
            experts.require_section(item)
        new_id = ce.save_section(d.get("name"), uid, item).id
    elif op == "section_delete" and item is not None:
        experts.require_section(item)
        ce.delete_section(item, uid)
    elif op == "lesson_add":
        sid = d.get("section_id") if isinstance(d.get("section_id"), int) else -1
        experts.require_section(sid)
        new_id = ce.add_lesson(sid, d.get("name"), uid).id
    elif op == "lesson_delete" and item is not None:
        experts.require_section(_section_of_topic(item))
        ce.delete_lesson(item, uid)
    elif op == "move" and item is not None:
        experts.require_section(item if d.get("kind") == "section" else _section_of_topic(item))
        ce.move(d.get("kind"), item, d.get("step"))
    else:
        raise ce.EditError(_("Amal noto‘g‘ri"))
    return jsonify(ok=True, id=new_id, tree=ce.tree(experts.my_areas()))


@bp.get("/mavzular/dars/<int:tid>")
def lesson_get(tid):
    experts.require_section(_section_of_topic(tid))
    data = ce.lesson(tid)
    return jsonify(ok=True, lesson=data) if data else (jsonify(ok=False, error=_("Dars topilmadi")), 404)


@bp.post("/mavzular/dars/<int:tid>")
@_json_errors
def lesson_save(tid):
    experts.require_section(_section_of_topic(tid))
    d = request.get_json(silent=True)
    data = ce.save_lesson(tid, d if isinstance(d, dict) else {}, current_user.id)
    return jsonify(ok=True, lesson=data, tree=ce.tree(experts.my_areas()))


@bp.post("/mavzular/rasm")
@_json_errors
def lesson_image():
    src = save_image(request.files.get("image"))
    if not src:
        raise ce.EditError(_("Rasmni tanlang"))
    return jsonify(ok=True, src=src)


# ---------- E'tirozlar ----------

def _objections_ctx(qid=None):
    areas = experts.my_areas()
    items = rv.queue(areas)
    qid = qid or request.args.get("id", type=int) or (items[0]["id"] if items else None)
    d = rv.detail(qid) if any(o["id"] == qid for o in items) else None
    return {"items": items, "d": d, "state": m.Q_STATE, "panel": "expert"}


@bp.get("/etirozlar")
def objections():
    return render_template("expert/objections.html", **_objections_ctx())


@bp.post("/etirozlar/<int:qid>")
def objection_decide(qid):
    _own_question(qid)
    action, errors, n = field("action"), {}, 0
    try:
        n = rv.decide(qid, current_user.id, action, field("verdict")[:2000],
                      [int(k) for k in request.form.getlist("keys") if k.isdigit()], field("accept").split(","))
    except qb.FormError as e:
        db.session.rollback()
        errors = e.errors
    to = url_for("expert.editor", id=qid) if action == "fix" else url_for("expert.objections")
    msg = None if errors else (_("Xulosa yuborildi, %(n)s ta natija qayta hisoblandi", n=n) if n else _("Xulosa yuborildi"))
    return respond(errors=errors, template="expert/objections.html", **(_objections_ctx(qid) if errors else {}), redirect_to=to, message=msg)


@bp.post("/etirozlar/<int:qid>/toxtatish")
def objection_pause(qid):
    _own_question(qid)
    on = field("on") == "1"
    ok = rv.pause(qid, current_user.id, on)
    msg = (_("Savol testlardan vaqtincha to‘xtatildi") if on else _("Savol testlarga qaytarildi")) if ok else _("Savol holati o‘zgarmadi")
    return respond(redirect_to=url_for("expert.objections", id=qid), message=msg)
