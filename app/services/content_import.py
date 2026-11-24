"""Kontentni JSON fayldan bazaga yuklash: kurs → bo'limlar → mavzular → kichik mavzular → dars bloklari va savollar.

Buyruq: `flask kontent-yuklash [FAYL] [--holat review|approved|draft]`. Fayl berilmasa namunaviy kontent yuklanadi
(app/seed/namuna_kontent.json). Format o'sha faylda va docs/kontent-formati.md da.

Qoidalar:
- Avval butun fayl tekshiriladi; bitta xato bo'lsa ham bazaga hech narsa yozilmaydi (xatolar yo'li bilan chiqadi).
- Qayta yuklash xavfsiz: kurs slug bo'yicha, bo'lim/mavzu/kichik mavzu nomi bo'yicha topiladi va yangilanadi;
  blok matn xeshi bo'yicha, savol shu kichik mavzudagi matni bo'yicha takrorlanmaydi. Mavjud savol o'zgartirilmaydi
  (tasdiqlangan savolni jimgina almashtirmaslik uchun) — uni ekspert panelida tahrirlash kerak.
- Har bir yangi savol uchun 1-versiya (question_versions) yoziladi: test urinishlari shunga havola qiladi.

Javob formatlari (variant indekslari 0 dan):
- single:   data.options [≥2], answer {"keys": [i]}
- multiple: data.options [≥2], answer {"keys": [i, j, ...]}
  (ikkalasida ixtiyoriy answer.notes — har bir variantning izohi, «Yechimini ko'rish»da chiqadi)
- open:     answer {"value": "45", "accept": ["45", "qirq besh"]}   (accept — ixtiyoriy qo'shimcha to'g'ri javoblar)
- matching: data.left [≥2], data.right [shuncha], answer {"pairs": [r0, r1, ...]} — left[k] ↔ right[pairs[k]]
"""
import hashlib
import json
from dataclasses import dataclass, field

from sqlalchemy import select

from ..extensions import db
from ..models import ContentBlock, Course, Question, QuestionVersion, Section, Subtopic, Topic
from ..models.content import BLOCK_KINDS
from ..models.questions import Q_DIFFICULTY, Q_STATUS, Q_TYPES
from .question_templates import TEMPLATES


class ContentError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__(f"{len(errors)} ta xato")
        self.errors = errors


@dataclass
class Report:
    created: dict = field(default_factory=lambda: {"sections": 0, "topics": 0, "subtopics": 0, "blocks": 0, "questions": 0})
    skipped_questions: int = 0


# ---------------- Tekshiruv ----------------

def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


def _str_list(v, min_len):
    return isinstance(v, list) and len(v) >= min_len and all(_is_str(x) for x in v)


def _int_list(v):
    return isinstance(v, list) and all(isinstance(x, int) and not isinstance(x, bool) for x in v)


def check_question(q) -> list[str]:
    """Bitta savolni tekshiradi; xatolar ro'yxatini qaytaradi (bo'sh — to'g'ri)."""
    if not isinstance(q, dict):
        return ["savol obyekt bo'lishi kerak"]
    errs = []
    t, data, ans = q.get("type"), q.get("data") or {}, q.get("answer")
    if t not in Q_TYPES:
        return [f"type {Q_TYPES} dan biri bo'lishi kerak, berilgan: {t!r}"]
    if q.get("difficulty") not in Q_DIFFICULTY:
        errs.append(f"difficulty {Q_DIFFICULTY} dan biri bo'lishi kerak")
    if not _is_str(q.get("text")):
        errs.append("text bo'sh")
    if q.get("source", "import") not in ("import", "ai"):
        errs.append("source: import yoki ai")
    if not isinstance(data, dict) or not isinstance(ans, dict):
        return errs + ["data va answer obyekt bo'lishi kerak"]
    if t in ("single", "multiple"):
        opts, keys = data.get("options"), ans.get("keys")
        if not _str_list(opts, 2):
            errs.append("data.options: kamida 2 ta bo'sh bo'lmagan variant")
        elif not _int_list(keys) or not keys or any(not 0 <= k < len(opts) for k in keys) or len(set(keys)) != len(keys):
            errs.append(f"answer.keys: 0..{len(opts) - 1} oralig'idagi takrorlanmas indekslar")
        elif t == "single" and len(keys) != 1:
            errs.append("single savolda answer.keys da aynan 1 ta indeks bo'ladi")
        notes = ans.get("notes")
        if notes is not None and (not isinstance(notes, list) or not isinstance(opts, list) or len(notes) != len(opts)
                                  or not all(isinstance(n, str) for n in notes)):
            errs.append("answer.notes: har bir variantga bittadan izoh (matn)")
    elif t == "open":
        if not _is_str(ans.get("value")):
            errs.append("answer.value bo'sh")
        if "accept" in ans and not _str_list(ans["accept"], 0):
            errs.append("answer.accept satrlar ro'yxati bo'lishi kerak")
    elif t == "matching":
        left, right, pairs = data.get("left"), data.get("right"), ans.get("pairs")
        if not _str_list(left, 2) or not _str_list(right, 2) or len(left) != len(right):
            errs.append("data.left va data.right: bir xil uzunlikdagi, kamida 2 ta elementli ro'yxatlar")
        elif not _int_list(pairs) or sorted(pairs) != list(range(len(right))):
            errs.append(f"answer.pairs: 0..{len(right) - 1} sonlarining o'rin almashtirishi (har biri bir marta)")
    return errs


def check(doc) -> list[str]:
    """Butun faylni tekshiradi. Xato yo'li: sections[0].topics[1].subtopics[0].questions[2]: ..."""
    errs = []
    if not isinstance(doc, dict):
        return ["fayl JSON obyekt bo'lishi kerak"]
    course = doc.get("course") or {}
    if not _is_str(course.get("slug")) or not _is_str(course.get("title")):
        errs.append("course: slug va title kerak")
    sections = doc.get("sections")
    if not isinstance(sections, list) or not sections:
        return errs + ["sections: bo'sh bo'lmagan ro'yxat kerak"]
    for si, s in enumerate(sections):
        sp = f"sections[{si}]"
        if not isinstance(s, dict) or not _is_str(s.get("title")):
            errs.append(f"{sp}: title kerak")
            continue
        for ti, t in enumerate(s.get("topics") or []):
            tp = f"{sp}.topics[{ti}]"
            if not isinstance(t, dict) or not _is_str(t.get("title")):
                errs.append(f"{tp}: title kerak")
                continue
            if not t.get("subtopics"):
                errs.append(f"{tp}: kamida bitta kichik mavzu kerak")
            for ui, u in enumerate(t.get("subtopics") or []):
                up = f"{tp}.subtopics[{ui}]"
                if not isinstance(u, dict) or not _is_str(u.get("title")):
                    errs.append(f"{up}: title kerak")
                    continue
                w = u.get("weight", 1)
                if not isinstance(w, int) or isinstance(w, bool) or not 0 <= w <= 50:
                    errs.append(f"{up}: weight 0..50 butun son")
                gens = u.get("generators", [])
                if not isinstance(gens, list) or any(g not in TEMPLATES for g in gens if isinstance(g, str)) \
                        or not all(isinstance(g, str) for g in gens):
                    errs.append(f"{up}: generators — shablon nomlari ro'yxati: {', '.join(TEMPLATES)}")
                for bi, b in enumerate(u.get("blocks") or []):
                    if not isinstance(b, dict) or b.get("kind") not in BLOCK_KINDS or not isinstance(b.get("data"), dict):
                        errs.append(f"{up}.blocks[{bi}]: kind {BLOCK_KINDS} dan biri va data obyekt bo'lishi kerak")
                texts = set()
                for qi, q in enumerate(u.get("questions") or []):
                    qp = f"{up}.questions[{qi}]"
                    errs += [f"{qp}: {e}" for e in check_question(q)]
                    if isinstance(q, dict) and _is_str(q.get("text")):
                        key = (q["text"].strip(), json.dumps(q.get("data") or {}, sort_keys=True))
                        if key in texts:
                            errs.append(f"{qp}: shu kichik mavzuda bir xil savol ikki marta")
                        texts.add(key)
    return errs


# ---------------- Yozish ----------------

def _hash(kind: str, data: dict) -> str:
    return hashlib.sha256((kind + json.dumps(data, sort_keys=True, ensure_ascii=False)).encode()).hexdigest()


def _get_or_create(model, where: dict, report_key: str | None, report: Report, **values):
    obj = db.session.scalar(select(model).filter_by(**where))
    if obj is None:
        obj = model(**where, **values)
        db.session.add(obj)
        db.session.flush()
        if report_key:
            report.created[report_key] += 1
    else:
        for k, v in values.items():
            setattr(obj, k, v)
    return obj


def _question_key(subtopic_id: int, text: str, data: dict) -> bool:
    """Shu kichik mavzuda xuddi shu matn va ma'lumotli savol bormi (kod/jadval farqli bir xil matnlar alohida savol)."""
    rows = db.session.scalars(select(Question.data).where(Question.subtopic_id == subtopic_id, Question.text == text))
    return any(r == data for r in rows)


def load(doc: dict, status: str = "review") -> Report:
    """Tekshiradi va yozadi (bitta tranzaksiya). Xato bo'lsa ContentError, bazaga hech narsa yozilmaydi."""
    if status not in Q_STATUS:
        raise ContentError([f"holat {Q_STATUS} dan biri bo'lishi kerak"])
    errors = check(doc)
    if errors:
        raise ContentError(errors)
    report = Report()
    try:
        c = doc["course"]
        course = _get_or_create(Course, {"slug": c["slug"]}, None, report, title=c["title"])
        for si, s in enumerate(doc["sections"]):
            section = _get_or_create(Section, {"course_id": course.id, "title": s["title"]}, "sections", report, position=si)
            for ti, t in enumerate(s.get("topics") or []):
                topic = _get_or_create(Topic, {"section_id": section.id, "title": t["title"]}, "topics", report,
                                       position=ti, est_minutes=t.get("est_minutes"),
                                       is_published=t.get("published", True))
                for ui, u in enumerate(t["subtopics"]):
                    sub = _get_or_create(Subtopic, {"topic_id": topic.id, "title": u["title"]}, "subtopics", report,
                                         position=ui, weight=u.get("weight", 1),
                                         **({"generators": u["generators"]} if "generators" in u else {}))
                    _load_blocks(sub, u.get("blocks") or [], report)
                    _load_questions(sub, u.get("questions") or [], status, report)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return report


def _load_blocks(sub: Subtopic, blocks: list, report: Report):
    existing = set(db.session.scalars(select(ContentBlock.content_hash).where(ContentBlock.subtopic_id == sub.id)))
    for bi, b in enumerate(blocks):
        h = _hash(b["kind"], b["data"])
        if h in existing:
            continue
        db.session.add(ContentBlock(subtopic_id=sub.id, kind=b["kind"], position=bi, data=b["data"], content_hash=h,
                                    audio_text=b.get("audio_text"), method=b.get("method")))
        existing.add(h)
        report.created["blocks"] += 1


def _load_questions(sub: Subtopic, questions: list, status: str, report: Report):
    for q in questions:
        text, data = q["text"].strip(), q.get("data") or {}
        if _question_key(sub.id, text, data):
            report.skipped_questions += 1
            continue
        # AI tuzgan savol har doim ekspert tekshiruviga tushadi (Tekshiruv navbati), --holat unga ta'sir qilmaydi
        source = q.get("source", "import")
        row = Question(subtopic_id=sub.id, type=q["type"], difficulty=q["difficulty"], text=text, data=data,
                       answer=q["answer"], explanation=q.get("explanation"), source=source,
                       status="review" if source == "ai" else status, time_limit_s=q.get("time_limit_s"))
        db.session.add(row)
        db.session.flush()
        db.session.add(QuestionVersion(question_id=row.id, version=1, change_note="import"))
        report.created["questions"] += 1
