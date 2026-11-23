"""Savollar banki (ekspert paneli): ro'yxat va filtrlar, yaratish/tahrirlash (versiyalar bilan), arxivlash,
AI savollari navbati (tasdiqlash/rad etish), «savollar yetarli emas» ogohlantirishi. Har bir o'zgarish audit_log'da.

Ekspert panelidagi atamalar: «Mavzu» = sections, «Dars» = topics, «Kichik mavzu» = subtopics.

Qoidalar:
- Tahrir savolni joyida o'zgartiradi va versiyani oshiradi; eski holat question_versions'da qoladi —
  avvalgi test urinishlari o'z versiyasiga havola qilgani uchun natijalar buzilmaydi.
- «O'chirish» — arxivlash (status=archived): savol testlarga tushmaydi, lekin tarix saqlanadi.
- AI savolini rad etish: hech kimga berilmagan bo'lsa butunlay o'chiriladi, aks holda arxivlanadi.
"""
from dataclasses import dataclass

from flask import has_request_context, request
from sqlalchemy import func, select

from ..extensions import db
from ..models import AttemptItem, AuditLog, Question, QuestionVersion, Section, Subtopic, Topic
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

def content_tree() -> list[dict]:
    """[{"id", "name", "lessons": [{"id", "name", "questions", "subtopics": [{"id", "name"}]}]}] — tanlovlar uchun."""
    counts = dict(db.session.execute(
        select(Subtopic.topic_id, func.count(Question.id)).join(Question, Question.subtopic_id == Subtopic.id)
        .where(Question.status != "archived").group_by(Subtopic.topic_id)).all())
    rows = db.session.execute(
        select(Section.id, Section.title, Topic.id, Topic.title, Subtopic.id, Subtopic.title)
        .join(Topic, Topic.section_id == Section.id).join(Subtopic, Subtopic.topic_id == Topic.id)
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


def list_questions(f: Filters, page: int = 1, *, source: str | None = None, status: str | None = None):
    """→ (sahifadagi qatorlar, topilganlar soni, sahifalar soni). Arxivlangan savollar faqat holat=archived filtrida."""
    base = (select(Question, Subtopic.title, Topic.title, Section.title)
            .join(Subtopic, Question.subtopic_id == Subtopic.id).join(Topic, Subtopic.topic_id == Topic.id)
            .join(Section, Topic.section_id == Section.id))
    base = _apply(base, f)
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


def shortage() -> list[dict]:
    """Tasdiqlangan savollari yetarli bo'lmagan kichik mavzular: har bir daraja bo'yicha < MIN_RATIO × weight."""
    approved = select(Question.subtopic_id, Question.difficulty, func.count().label("n")) \
        .where(Question.status == "approved").group_by(Question.subtopic_id, Question.difficulty).subquery()
    rows = db.session.execute(
        select(Subtopic.id, Subtopic.title, Topic.title, Subtopic.weight,
               func.coalesce(func.min(approved.c.n), 0), func.count(approved.c.difficulty))
        .join(Topic, Subtopic.topic_id == Topic.id)
        .outerjoin(approved, approved.c.subtopic_id == Subtopic.id)
        .where(Subtopic.weight > 0, Topic.is_published.is_(True))
        .group_by(Subtopic.id, Subtopic.title, Topic.title, Subtopic.weight)).all()
    need = len(LEVEL_TO_DIFF)
    return [{"id": sid, "name": name, "topic": topic, "need": MIN_RATIO * w}
            for sid, name, topic, w, least, levels in rows if levels < need or least < MIN_RATIO * w]


# ---------------- Saqlash ----------------

class FormError(ValueError):
    def __init__(self, errors: dict):
        super().__init__("forma xatosi")
        self.errors = errors


def save(payload: dict, actor_id: int, question_id: int | None = None, status: str = "approved") -> Question:
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
        for k, v in fields.items():
            setattr(q, k, v)
        if _snapshot(q) == before and q.status == status:
            return q
        q.status = status
        if _snapshot(q) != before:
            q.version += 1
        action = "update"
    if not db.session.scalar(select(QuestionVersion.id).where(QuestionVersion.question_id == q.id,
                                                              QuestionVersion.version == q.version)):
        db.session.add(QuestionVersion(question_id=q.id, version=q.version, snapshot=_snapshot(q), changed_by=actor_id,
                                       change_note=action))
    audit(actor_id, action, q.id, {"before": before, "after": _snapshot(q), "status": q.status})
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
    """AI savolini rad etish: hech kimga berilmagan bo'lsa o'chiriladi, berilgan bo'lsa arxivlanadi."""
    q = db.session.get(Question, question_id)
    if q is None or q.source != "ai" or q.status != "review":
        return False
    used = db.session.scalar(select(func.count()).select_from(AttemptItem).where(AttemptItem.question_id == q.id))
    audit(actor_id, "reject", q.id, {"before": _snapshot(q)})
    if used:
        q.status = "archived"
    else:
        db.session.delete(q)   # question_versions ON DELETE CASCADE
    db.session.commit()
    return True


def get(question_id: int) -> Question | None:
    return db.session.get(Question, question_id)
