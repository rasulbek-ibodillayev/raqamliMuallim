"""Savollar banki (ekspert paneli): ro'yxat va filtrlar, yaratish/tahrirlash (versiyalar bilan), arxivlash,
AI savollari navbati (tasdiqlash/rad etish), «savollar yetarli emas» ogohlantirishi. Har bir o'zgarish audit_log'da.

Ekspert panelidagi atamalar: «Mavzu» = sections, «Dars» = topics, «Kichik mavzu» = subtopics.

Qoidalar:
- Tahrir savolni joyida o'zgartiradi va versiyani oshiradi; eski holat question_versions'da qoladi (services/versions.py) —
  avvalgi test urinishlari o'z versiyasiga havola qilgani uchun natijalar buzilmaydi.
- «O'chirish» — arxivlash (status=archived): savol testlarga tushmaydi, lekin tarix saqlanadi.
- AI savolini rad etish: hech kimga berilmagan bo'lsa butunlay o'chiriladi, aks holda arxivlanadi.
"""
from dataclasses import dataclass

from flask import has_request_context, request
from sqlalchemy import func, select, true, update

from ..extensions import db
from ..models import AuditLog, Question, QuestionVersion, Section, Subtopic, Topic
from . import notify, recalc, seen
from .content_import import check_question

PAGE = 20
QUEUE_PAGE = 5
MIN_RATIO = 4   # har kichik mavzu va daraja bo'yicha testdagidan kamida 4 baravar ko'p tasdiqlangan savol

# Formadagi qiymatlar ↔ bazadagi qiymatlar
KIND_TO_TYPE = {"yopiq": "single", "kop": "multiple", "moslash": "matching", "ochiq": "open"}
TYPE_TO_KIND = {v: k for k, v in KIND_TO_TYPE.items()}
LEVEL_TO_DIFF = {"Oson": "easy", "O‘rta": "medium", "Qiyin": "hard"}
DIFF_TO_LEVEL = {v: k for k, v in LEVEL_TO_DIFF.items()}
STATUSES = ("approved", "review", "draft", "paused", "archived")


def audit(actor_id: int | None, action: str, entity_id, data: dict | None = None):
    db.session.add(AuditLog(actor_id=actor_id, action=action, entity="question", entity_id=str(entity_id),
                            data=data or {}, ip=request.remote_addr if has_request_context() else None))


def _snapshot(q: Question) -> dict:
    return {k: getattr(q, k) for k in ("type", "difficulty", "text", "data", "answer", "explanation", "subtopic_id",
                                       "time_limit_s")}


# ---------------- Kontent daraxti ----------------

def content_tree(areas: set[int] | None = None) -> list[dict]:
    """[{"id", "name", "lessons": [{"id", "name", "questions", "subtopics": [{"id", "name"}]}]}] — tanlovlar uchun."""
    counts = dict(db.session.execute(
        select(Subtopic.topic_id, func.count(Question.id)).join(Question, Question.subtopic_id == Subtopic.id)
        .where(Question.status != "archived").group_by(Subtopic.topic_id)).all())
    rows = db.session.execute(
        select(Section.id, Section.title, Topic.id, Topic.title, Subtopic.id, Subtopic.title)
        .join(Topic, Topic.section_id == Section.id).join(Subtopic, Subtopic.topic_id == Topic.id)
        .where(Section.id.in_(areas) if areas is not None else true())
        .order_by(Section.position, Section.id, Topic.position, Topic.id, Subtopic.position, Subtopic.id)).all()
    tree: dict[int, dict] = {}
    for sid, sname, tid, tname, uid, uname in rows:
        sec = tree.setdefault(sid, {"id": sid, "name": sname, "lessons": {}})
        les = sec["lessons"].setdefault(tid, {"id": tid, "name": tname, "questions": counts.get(tid, 0), "subtopics": []})
        les["subtopics"].append({"id": uid, "name": uname})
    return [{**s, "lessons": list(s["lessons"].values())} for s in tree.values()]


# ---------------- Ro'yxat ----------------

@dataclass
class Filters:
    q: str = ""
    mavzu: str = ""      # section id
    dars: str = ""       # topic id
    daraja: str = ""     # Oson / O‘rta / Qiyin
    turi: str = ""       # yopiq / kop / moslash / ochiq
    holat: str = ""      # approved / review / ...

    @classmethod
    def from_args(cls, args):
        return cls(**{k: (args.get(k) or "").strip() for k in cls.__dataclass_fields__})

    def active(self) -> bool:
        return any(vars(self).values())


def _apply(stmt, f: Filters):
    if f.q:
        like = f.q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        stmt = stmt.where(Question.text.ilike("%" + like + "%", escape="\\"))
    if f.mavzu.isdigit():
        stmt = stmt.where(Topic.section_id == int(f.mavzu))
    if f.dars.isdigit():
        stmt = stmt.where(Topic.id == int(f.dars))
    if f.daraja in LEVEL_TO_DIFF:
        stmt = stmt.where(Question.difficulty == LEVEL_TO_DIFF[f.daraja])
    if f.turi in KIND_TO_TYPE:
        stmt = stmt.where(Question.type == KIND_TO_TYPE[f.turi])
    return stmt


def list_questions(f: Filters, page: int = 1, *, source: str | None = None, status: str | None = None,
                   areas: set[int] | None = None):
    """→ (sahifadagi qatorlar, topilganlar soni, sahifalar soni). Arxivlangan savollar faqat holat=archived filtrida."""
    base = (select(Question, Subtopic.title, Topic.title, Section.title)
            .join(Subtopic, Question.subtopic_id == Subtopic.id).join(Topic, Subtopic.topic_id == Topic.id)
            .join(Section, Topic.section_id == Section.id))
    base = _apply(base, f)
    if areas is not None:
        base = base.where(Section.id.in_(areas))
    st = status or (f.holat if f.holat in STATUSES else None)
    base = base.where(Question.status == st) if st else base.where(Question.status != "archived")
    if source:
        base = base.where(Question.source == source)
    total = db.session.scalar(select(func.count()).select_from(base.subquery()))
    size = QUEUE_PAGE if source == "ai" else PAGE
    pages = max(1, -(-total // size))
    page = min(max(1, page), pages)
    rows = db.session.execute(base.order_by(Question.updated_at.desc(), Question.id.desc())
                              .offset((page - 1) * size).limit(size)).all()
    return [_row(q, sub, top, sec) for q, sub, top, sec in rows], total, pages, page


def _row(q: Question, sub: str, top: str, sec: str) -> dict:
    pct = round(100 * q.times_correct / q.times_answered) if q.times_answered else None
    # Daraja shubhali: yetarli javob bo'yicha oson savolni kam, qiyinini juda ko'p odam topyapti
    doubt = q.times_answered >= 20 and ((q.difficulty == "easy" and pct < 50) or (q.difficulty == "hard" and pct > 90))
    return {"id": q.id, "text": q.text, "section": sec, "topic": top, "subtopic": sub, "status": q.status,
            "level": DIFF_TO_LEVEL[q.difficulty], "kind": TYPE_TO_KIND[q.type], "pct": pct, "doubt": doubt,
            "source": q.source, "created": q.created_at, **_options(q)}


def _options(q: Question) -> dict:
    """Navbat kartasi uchun: variantlar va to'g'ri javob indekslari (ochiq — bitta qiymat, moslash — juftliklar)."""
    d, a = q.data or {}, q.answer or {}
    if q.type in ("single", "multiple"):
        return {"options": d.get("options", []), "right": a.get("keys", [])}
    if q.type == "open":
        return {"options": [a.get("value", "")], "right": [0]}
    left, right = d.get("left", []), d.get("right", [])
    return {"options": [f"{l} — {right[r]}" for l, r in zip(left, a.get("pairs", [])) if r < len(right)],
            "right": list(range(len(left)))}


def shortage(areas: set[int] | None = None) -> list[dict]:
    """Tasdiqlangan savollari yetarli bo'lmagan kichik mavzular: har bir daraja bo'yicha < MIN_RATIO × weight."""
    approved = select(Question.subtopic_id, Question.difficulty, func.count().label("n")) \
        .where(Question.status == "approved").group_by(Question.subtopic_id, Question.difficulty).subquery()
    rows = db.session.execute(
        select(Subtopic.id, Subtopic.title, Topic.title, Subtopic.weight,
               func.coalesce(func.min(approved.c.n), 0), func.count(approved.c.difficulty))
        .join(Topic, Subtopic.topic_id == Topic.id)
        .outerjoin(approved, approved.c.subtopic_id == Subtopic.id)
        .where(Subtopic.weight > 0, Topic.is_published.is_(True),
               Topic.section_id.in_(areas) if areas is not None else true())
        .group_by(Subtopic.id, Subtopic.title, Topic.title, Subtopic.weight)).all()
    need = len(LEVEL_TO_DIFF)
    return [{"id": sid, "name": name, "topic": topic, "need": MIN_RATIO * w}
            for sid, name, topic, w, least, levels in rows if levels < need or least < MIN_RATIO * w]


# ---------------- Saqlash ----------------

class FormError(ValueError):
    def __init__(self, errors: dict):
        super().__init__("forma xatosi")
        self.errors = errors


def save(payload: dict, actor_id: int, question_id: int | None = None, status: str = "approved", *,
         commit: bool = True) -> Question:
    """payload: subtopic_id, type, difficulty, text, data, answer, explanation, time_limit_s. Tekshiradi va yozadi.
    Yangi savol — 1-versiya; tahrir — o'zgargan bo'lsa versiya +1."""
    errs = check_question(payload)
    if errs:
        raise FormError({"text": errs[0]})
    if db.session.get(Subtopic, payload["subtopic_id"]) is None:
        raise FormError({"subtopic": "Kichik mavzu topilmadi"})
    fields = {k: payload.get(k) for k in ("subtopic_id", "type", "difficulty", "text", "data", "answer", "explanation",
                                          "time_limit_s")}
    if question_id is None:
        q = Question(**fields, source="expert", status=status, author_id=actor_id, version=1)
        db.session.add(q)
        db.session.flush()
        action, before = "create", None
    else:
        q = db.session.get(Question, question_id)
        if q is None:
            raise FormError({"text": "Savol topilmadi"})
        before = _snapshot(q)
        # Muharrirda variant izohlari maydoni yo'q: variantlar o'zgarmagan bo'lsa, izohlar saqlanib qoladi
        notes = (q.answer or {}).get("notes")
        if notes and "notes" not in fields["answer"] and (q.data or {}).get("options") == (fields["data"] or {}).get("options"):
            fields["answer"] = {**fields["answer"], "notes": notes}
        for k, v in fields.items():
            setattr(q, k, v)
        if _snapshot(q) == before and q.status == status:
            return q
        q.status = status
        if _snapshot(q) != before:                      # avvalgi versiyaga nusxasi yoziladi, yangisiniki — questions'ning o'zi
            db.session.execute(update(QuestionVersion).where(QuestionVersion.question_id == q.id, QuestionVersion.version == q.version)
                               .values(snapshot=before))
            q.version += 1
        action = "update"
    if not db.session.scalar(select(QuestionVersion.id).where(QuestionVersion.question_id == q.id,
                                                              QuestionVersion.version == q.version)):
        db.session.add(QuestionVersion(question_id=q.id, version=q.version, changed_by=actor_id, change_note=action))
    # Mazmuni versiyalarda: jurnalga faqat nima o'zgargani yoziladi
    now = _snapshot(q)
    audit(actor_id, action, q.id, {"version": q.version, "status": q.status,
                                   **({"changed": [k for k in now if now[k] != before[k]]} if before else {})})
    if commit:
        db.session.commit()
    return q


def archive(question_id: int, actor_id: int) -> bool:
    q = db.session.get(Question, question_id)
    if q is None or q.status == "archived":
        return False
    q.status = "archived"
    audit(actor_id, "archive", q.id)
    db.session.commit()
    return True


def reject(question_id: int, actor_id: int) -> bool:
    """AI savolini rad etish: hech kimga berilmagan bo'lsa o'chiriladi; berilgan bo'lsa arxivlanadi, natijalardan
    chiqariladi va savol berilgan foydalanuvchilarga bildirishnoma boradi (eski va yangi foiz bilan)."""
    q = db.session.get(Question, question_id)
    if q is None or q.source != "ai" or q.status != "review":
        return False
    used = seen.ever_given(q.id)
    audit(actor_id, "reject", q.id, {"before": _snapshot(q)})
    if used:
        q.status = "archived"
        for c in recalc.drop(q.id):
            notify.add(c.user_id, notify.DROPPED, c.attempt_id, c.old, c.new)
    else:
        db.session.delete(q)   # question_versions ON DELETE CASCADE
    db.session.commit()
    return True


def get(question_id: int) -> Question | None:
    return db.session.get(Question, question_id)


# ---------------- Excel orqali import ----------------
# Bir qator — bitta savol. Ustunlar: EXCEL_HEAD. Savol turlari:
#   yopiq — A..F variantlar, «To'g'ri javob»: bitta harf (B);
#   ko'p javobli — A..F variantlar, «To'g'ri javob»: harflar vergul bilan (A, C);
#   moslashtirish — A..F kataklarda «atama = ta'rif» juftliklari, «To'g'ri javob» bo'sh;
#   ochiq — variantlar bo'sh, «To'g'ri javob»: javob; boshqa yozilishlari «;» bilan (45; qirq besh).
# «Qo'shimcha» — eksportda kod, jadval yoki rasm borligini bildiradi: bunday qatorlar importda o'tkazib yuboriladi (Excel'da
# to'liq ifodalanmaydi). Bazada aynan bor savol ham o'tkaziladi: eksport qilingan faylni qayta yuklash takrorlamaydi.
# Fayl to'liq tekshiriladi: bitta qatorda xato bo'lsa ham hech narsa yozilmaydi.
EXCEL_HEAD = ["Mavzu", "Dars", "Kichik mavzu", "Qiyinlik", "Savol turi", "Savol matni",
              "A", "B", "C", "D", "E", "F", "To‘g‘ri javob", "Vaqt (soniya)", "Izoh", "Qo‘shimcha"]
EXCEL_WIDTHS = [22, 24, 22, 10, 16, 48, 18, 18, 18, 18, 12, 12, 14, 12, 36, 16]
EXPORT_MAX = 5000
_LETTERS = "ABCDEF"


def _norm(s: str) -> str:
    """Katta-kichik harf va o'zbekcha apostrof shakllari farqlanmaydi."""
    return " ".join(str(s).lower().replace("ʻ", "'").replace("‘", "'").replace("’", "'").replace("`", "'").split())


_KIND_NAMES = {"yopiq": "yopiq", "bitta javob": "yopiq", "ko'p javobli": "kop", "kop": "kop", "ko'p javob": "kop",
               "moslashtirish": "moslash", "moslash": "moslash", "ochiq": "ochiq", "ochiq javob": "ochiq"}
_LEVEL_NAMES = {_norm(k): k for k in LEVEL_TO_DIFF}


def excel_sample() -> bytes:
    """Namunaviy fayl: sarlavha va har bir savol turiga bittadan misol (bazadagi birinchi kichik mavzu bilan)."""
    from . import xlsx
    tree = content_tree()
    if tree and tree[0]["lessons"] and tree[0]["lessons"][0]["subtopics"]:
        sec, les = tree[0], tree[0]["lessons"][0]
        where = [sec["name"], les["name"], les["subtopics"][0]["name"]]
    else:
        where = ["Dasturlash asoslari", "Python: shart operatorlari", "if operatori"]
    rows = [EXCEL_HEAD,
            where + ["Oson", "yopiq", "x = 5 bo‘lsa, «if x > 3: print(x * 2)» nima chiqaradi?", "5", "10", "15", "Xato beradi",
                     "", "", "B", "60", "x > 3 rost, shuning uchun 5 * 2 = 10."],
            where + ["O‘rta", "ko‘p javobli", "Qaysilari taqqoslash amallari?", "==", "!=", "=", ">=", "", "", "A, B, D", "90", ""],
            where + ["O‘rta", "moslashtirish", "Amallarni ma’nosi bilan moslang.", "== = teng", "!= = teng emas",
                     "> = katta", "", "", "", "", "120", ""],
            where + ["Qiyin", "ochiq", "101101₂ sonini o‘nlik sanoq sistemasida yozing.", "", "", "", "", "", "",
                     "45; qirq besh", "90", "32 + 8 + 4 + 1 = 45"]]
    return xlsx.write(rows, widths=EXCEL_WIDTHS)


def _subtopic_index(areas: set[int] | None = None) -> dict[tuple[str, str, str], int]:
    return {(_norm(s["name"]), _norm(l["name"]), _norm(u["name"])): u["id"]
            for s in content_tree(areas) for l in s["lessons"] for u in l["subtopics"]}


def _excel_payload(row: list[str], subs: dict) -> tuple[dict | None, str | None]:
    row = (row + [""] * len(EXCEL_HEAD))[:len(EXCEL_HEAD)]
    sec, les, sub, level, kind, text = row[:6]
    opts, right, time_s, why, extra = row[6:12], row[12], row[13], row[14], row[15]
    if extra:
        return None, None
    sid = subs.get((_norm(sec), _norm(les), _norm(sub)))
    if sid is None:
        return None, "mavzu, dars yoki kichik mavzu bazada topilmadi"
    if _norm(level) not in _LEVEL_NAMES:
        return None, "qiyinlik: Oson, O‘rta yoki Qiyin"
    k = _KIND_NAMES.get(_norm(kind))
    if k is None:
        return None, "savol turi: yopiq, ko‘p javobli, moslashtirish yoki ochiq"
    if not text:
        return None, "savol matni bo‘sh"
    t = time_s or "60"
    if not (t.isdigit() and 10 <= int(t) <= 1800):
        return None, "vaqt 10–1800 soniya oralig‘ida bo‘lsin"
    data, answer = {"format": "matn"}, {}
    if k == "ochiq":
        vals = [v.strip() for v in right.split(";") if v.strip()]
        if not vals:
            return None, "ochiq savolning to‘g‘ri javobini kiriting"
        answer = {"value": vals[0], **({"accept": vals[1:]} if vals[1:] else {})}
    elif k == "moslash":
        # «atama = ta'rif»: avval bo'sh joy bilan o'ralgan « = » qidiriladi (atamaning o'zida «=» bo'lishi mumkin: «== = teng»)
        pairs = [tuple(x.strip() for x in o.split(" = " if " = " in o else "=", 1)) for o in opts if "=" in o]
        pairs = [p for p in pairs if p[0] and p[1]]
        if len(pairs) < 2:
            return None, "moslashtirishda kamida 2 ta «atama = ta’rif» juftligi bo‘lsin"
        data.update(left=[a for a, _b in pairs], right=[b for _a, b in pairs])
        answer = {"pairs": list(range(len(pairs)))}
    else:
        keep = [i for i, o in enumerate(opts) if o]
        if len(keep) < 2:
            return None, "kamida 2 ta javob varianti bo‘lsin"
        marks = [x.strip().upper() for x in right.replace(";", ",").split(",") if x.strip()]
        if not marks or any(len(m) != 1 or m not in _LETTERS or _LETTERS.index(m) not in keep for m in marks):
            return None, "to‘g‘ri javob — to‘ldirilgan variant harfi (masalan: B yoki A, C)"
        idx = sorted({_LETTERS.index(m) for m in marks})
        if k == "yopiq" and len(idx) != 1:
            return None, "yopiq savolda bitta to‘g‘ri javob bo‘lsin"
        if k == "kop" and len(idx) < 2:
            return None, "ko‘p javobli savolda kamida 2 ta to‘g‘ri javob bo‘lsin"
        data["options"] = [opts[i] for i in keep]
        answer = {"keys": [keep.index(i) for i in idx]}
    payload = {"subtopic_id": sid, "type": KIND_TO_TYPE[k], "difficulty": LEVEL_TO_DIFF[_LEVEL_NAMES[_norm(level)]],
               "text": text[:3000], "data": data, "answer": answer, "explanation": why[:2000] or None,
               "time_limit_s": int(t)}
    errs = check_question(payload)
    return (None, errs[0]) if errs else (payload, None)


def _identity(type_: str, data: dict, answer: dict):
    """Savolni bir xil deb hisoblash uchun: turi, variantlari yoki juftliklari (o'ng ustun tartibi ahamiyatsiz), kodi, jadvali."""
    d = data or {}
    pairs = sorted((x, d["right"][r]) for x, r in zip(d.get("left", []), answer.get("pairs", []))) if type_ == "matching" else None
    return type_, d.get("options"), pairs, *(d.get(k) for k in ("code", "table", "image", "diagram"))


def _exists(p: dict) -> bool:
    new = _identity(p["type"], p["data"], p["answer"])
    return any(_identity(t, d, a) == new for t, d, a in db.session.execute(
        select(Question.type, Question.data, Question.answer).where(
            Question.subtopic_id == p["subtopic_id"], Question.text == p["text"], Question.status != "archived")))


def export_excel(f: Filters, areas: set[int] | None = None) -> bytes:
    """Filtrdagi savollar, import formatida (EXPORT_MAX tagacha)."""
    from . import xlsx
    q = (select(Question, Subtopic.title, Topic.title, Section.title)
         .join(Subtopic, Question.subtopic_id == Subtopic.id).join(Topic, Subtopic.topic_id == Topic.id)
         .join(Section, Topic.section_id == Section.id))
    q = _apply(q, f).where(Question.status == f.holat if f.holat in STATUSES else Question.status != "archived")
    if areas is not None:
        q = q.where(Section.id.in_(areas))
    q = q.order_by(Section.position, Section.id, Topic.position, Topic.id, Subtopic.position, Subtopic.id, Question.id)
    names = {"yopiq": "yopiq", "kop": "ko‘p javobli", "moslash": "moslashtirish", "ochiq": "ochiq"}
    rows = [EXCEL_HEAD]
    for x, sub, top, sec in db.session.execute(q.limit(EXPORT_MAX)):
        d, a = x.data or {}, x.answer or {}
        kind, opts, right = TYPE_TO_KIND[x.type], [], ""
        if kind in ("yopiq", "kop"):
            opts = d.get("options", [])
            right = ", ".join(_LETTERS[i] if i < len(_LETTERS) else str(i + 1) for i in a.get("keys", []))
        elif kind == "moslash":
            opts = [f"{left} = {d['right'][r]}" for left, r in zip(d.get("left", []), a.get("pairs", []))]
        else:
            right = "; ".join([a.get("value", ""), *a.get("accept", [])])
        extra = [label for key, label in (("code", "kod"), ("table", "jadval"), ("image", "rasm"), ("diagram", "chizma")) if d.get(key)]
        if len(opts) > len(_LETTERS):
            extra.append("6 tadan ko‘p variant")
        opts = (opts + [""] * len(_LETTERS))[:len(_LETTERS)]
        rows.append([sec, top, sub, DIFF_TO_LEVEL[x.difficulty], names[kind], x.text, *opts, right,
                     str(x.time_limit_s or 60), x.explanation or "", ", ".join(extra)])
    return xlsx.write(rows, widths=EXCEL_WIDTHS)


def import_excel(data: bytes, actor_id: int, areas: set[int] | None = None) -> tuple[int, list[str]]:
    """Excel fayldagi savollarni bankka qo'shadi. Natija: (qo'shilganlar soni, xatolar). Xato bo'lsa hech narsa yozilmaydi.
    Bazada bor savollar o'tkazib yuboriladi."""
    from . import xlsx
    try:
        rows = xlsx.read_rows(data)
    except xlsx.XlsxError as e:
        return 0, [str(e)]
    if rows and _norm(rows[0][0] if rows[0] else "") == _norm(EXCEL_HEAD[0]):
        rows = rows[1:]
    numbered = [(n, r) for n, r in enumerate(rows, start=2) if any(c for c in r)]
    if not numbered:
        return 0, ["Faylda savol topilmadi"]
    subs = _subtopic_index(areas)
    payloads, errors = [], []
    for n, row in numbered:
        p, err = _excel_payload(row, subs)
        if err:
            errors.append(f"{n}-qator: {err}")
        elif p is not None and not _exists(p):
            payloads.append(p)
    if errors:
        return 0, errors[:20] + ([f"… yana {len(errors) - 20} ta xato"] if len(errors) > 20 else [])
    for p in payloads:
        save(p, actor_id)
    audit(actor_id, "import_excel", "excel", {"count": len(payloads)})
    db.session.commit()
    return len(payloads), []
