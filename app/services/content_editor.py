"""«Mavzular va darslar» muharriri (ekspert): mavzu (sections) → dars (topics) → kichik mavzu (subtopics) → bloklar.

- Dars butunlay saqlanadi (kichik mavzular, bloklar, shablonlar bitta so'rovda). Boshqa ekspert orada saqlagan bo'lsa (rev
  mos emas) — hech narsa yozilmaydi: birovning ishi jimgina bosilib ketmaydi.
- Blok o'zgarsa versiyasi va mazmun xeshi (audio va AI kesh kaliti) yangilanadi, o'zgarmasa tegilmaydi.
- O'chirish: savoli bor kichik mavzu, dars va mavzu o'chmaydi (savollar va natijalar unga bog'langan) — dars nashrdan
  olinadi. Yangi dars nashr qilinmagan holda yaratiladi.
- Muharrir bilmaydigan turdagi bloklar (example, quiz) o'zgarmay qoladi.
"""
import hashlib
import re
from datetime import datetime

from flask_babel import gettext as _
from sqlalchemy import func, select

from ..extensions import db
from ..models import AuditLog, ContentBlock, Course, Question, Section, Subtopic, Topic
from .content_import import _hash
from .question_templates import TEMPLATES

NAME_MAX, TEXT_MAX, CODE_MAX, BLOCKS_MAX, SUBS_MAX = 120, 20_000, 10_000, 60, 40
EDITABLE = ("text", "code", "image", "table", "mermaid", "formula", "video", "callout", "links")
_IMG = re.compile(r"(uploads|img)/[\w./-]+\.(png|jpg|jpeg|webp|svg)")


class EditError(ValueError):
    """Foydalanuvchiga ko'rsatiladigan xato."""


class Conflict(EditError):
    pass


def _audit(actor_id: int, action: str, entity: str, entity_id, data: dict | None = None):
    db.session.add(AuditLog(actor_id=actor_id, action=action, entity=entity, entity_id=str(entity_id), data=data or {}))


def _name(value) -> str:
    name = " ".join(str(value or "").split())
    if not name:
        raise EditError(_("Nomini kiriting"))
    if len(name) > NAME_MAX:
        raise EditError(_("Nom %(n)s belgidan oshmasin", n=NAME_MAX))
    return name


# ---------------- Daraxt ----------------

def tree(areas: set[int] | None = None) -> list[dict]:
    """[{"id", "name", "lessons": [{"id", "name", "published", "subs", "blocks", "questions"}]}]"""
    questions = dict(db.session.execute(
        select(Subtopic.topic_id, func.count(Question.id)).join(Question, Question.subtopic_id == Subtopic.id)
        .where(Question.status != "archived").group_by(Subtopic.topic_id)).all())
    subs = dict(db.session.execute(select(Subtopic.topic_id, func.count()).group_by(Subtopic.topic_id)).all())
    blocks = dict(db.session.execute(
        select(Subtopic.topic_id, func.count(ContentBlock.id)).join(ContentBlock, ContentBlock.subtopic_id == Subtopic.id)
        .where(ContentBlock.is_active.is_(True)).group_by(Subtopic.topic_id)).all())
    q = select(Section).order_by(Section.position, Section.id)
    sections = {s.id: {"id": s.id, "name": s.title, "lessons": []} for s in db.session.scalars(
        q.where(Section.id.in_(areas)) if areas is not None else q)}
    for t in db.session.scalars(select(Topic).where(Topic.section_id.in_(sections)).order_by(Topic.position, Topic.id)):
        sections[t.section_id]["lessons"].append({"id": t.id, "name": t.title, "published": t.is_published,
                                                  "subs": subs.get(t.id, 0), "blocks": blocks.get(t.id, 0),
                                                  "questions": questions.get(t.id, 0)})
    return list(sections.values())


def _unique(model, where, name: str, skip_id: int | None, message: str):
    q = select(model.id).where(where, func.lower(model.title) == name.lower())
    if skip_id:
        q = q.where(model.id != skip_id)
    if db.session.scalar(q.limit(1)):
        raise EditError(message)


def save_section(name, actor_id: int, section_id: int | None = None) -> Section:
    name = _name(name)
    _unique(Section, Section.id.is_not(None), name, section_id, _("Bunday mavzu allaqachon bor"))
    if section_id is None:
        course = db.session.scalar(select(Course).where(Course.is_active.is_(True)).order_by(Course.id).limit(1))
        if course is None:
            course = Course(slug="informatika", title="Informatika")
            db.session.add(course)
            db.session.flush()
        pos = db.session.scalar(select(func.coalesce(func.max(Section.position), -1))) + 1
        s = Section(course_id=course.id, title=name, position=pos)
        db.session.add(s)
        db.session.flush()
    else:
        s = db.session.get(Section, section_id)
        if s is None:
            raise EditError(_("Mavzu topilmadi"))
        s.title = name
    _audit(actor_id, "update" if section_id else "create", "section", s.id, {"title": name})
    db.session.commit()
    return s


def add_lesson(section_id: int, name, actor_id: int) -> Topic:
    """Yangi dars: nashr qilinmagan, bitta bo'sh kichik mavzu bilan."""
    name = _name(name)
    if db.session.get(Section, section_id) is None:
        raise EditError(_("Mavzu topilmadi"))
    _unique(Topic, Topic.section_id == section_id, name, None, _("Bu mavzuda bunday dars allaqachon bor"))
    pos = db.session.scalar(select(func.coalesce(func.max(Topic.position), -1)).where(Topic.section_id == section_id)) + 1
    t = Topic(section_id=section_id, title=name, position=pos, is_published=False)
    db.session.add(t)
    db.session.flush()
    db.session.add(Subtopic(topic_id=t.id, title=name, position=0))
    _audit(actor_id, "create", "topic", t.id, {"title": name})
    db.session.commit()
    return t


def _has_questions(*where) -> bool:
    return db.session.scalar(select(Question.id).join(Subtopic, Subtopic.id == Question.subtopic_id)
                             .join(Topic, Topic.id == Subtopic.topic_id).where(*where).limit(1)) is not None


def delete_section(section_id: int, actor_id: int) -> None:
    s = db.session.get(Section, section_id)
    if s is None:
        raise EditError(_("Mavzu topilmadi"))
    if _has_questions(Topic.section_id == section_id):
        raise EditError(_("Bu mavzuning savollari bor, o‘chirib bo‘lmaydi. Darslarini nashrdan olishingiz mumkin"))
    _audit(actor_id, "delete", "section", s.id, {"title": s.title})
    db.session.execute(Section.__table__.delete().where(Section.id == section_id))
    db.session.commit()


def delete_lesson(topic_id: int, actor_id: int) -> None:
    t = db.session.get(Topic, topic_id)
    if t is None:
        raise EditError(_("Dars topilmadi"))
    if _has_questions(Topic.id == topic_id):
        raise EditError(_("Bu darsning savollari bor, o‘chirib bo‘lmaydi. Uni nashrdan olishingiz mumkin"))
    _audit(actor_id, "delete", "topic", t.id, {"title": t.title})
    db.session.execute(Topic.__table__.delete().where(Topic.id == topic_id))
    db.session.commit()


def move(kind: str, item_id: int, step: int) -> None:
    """Mavzu yoki darsni qo'shnisi bilan almashtiradi. Tartib raqamlari qayta yoziladi (0, 1, 2 …)."""
    model = {"section": Section, "topic": Topic}.get(kind)
    obj = db.session.get(model, item_id) if model else None
    if obj is None or step not in (-1, 1):
        raise EditError(_("Topilmadi"))
    q = select(model).order_by(model.position, model.id)
    rows = list(db.session.scalars(q.where(Topic.section_id == obj.section_id) if kind == "topic" else q))
    i = rows.index(obj)
    if 0 <= i + step < len(rows):
        rows[i], rows[i + step] = rows[i + step], rows[i]
    for n, r in enumerate(rows):
        r.position = n
    db.session.commit()


# ---------------- Dars ----------------

def _blocks(subtopic_ids):
    out: dict[int, list[ContentBlock]] = {}
    for b in db.session.scalars(select(ContentBlock).where(ContentBlock.subtopic_id.in_(subtopic_ids),
                                                           ContentBlock.is_active.is_(True))
                                .order_by(ContentBlock.position, ContentBlock.id)):
        out.setdefault(b.subtopic_id, []).append(b)
    return out


def _rev(t: Topic, subs, blocks) -> str:
    """Dars holatining izi: hamma qatorlar id'si va oxirgi o'zgarish vaqti."""
    parts: list[tuple[int, datetime]] = [(t.id, t.updated_at), *((s.id, s.updated_at) for s in subs),
                                         *((b.id, b.updated_at) for bs in blocks.values() for b in bs)]
    return hashlib.sha256(repr([(i, u.timestamp()) for i, u in parts]).encode()).hexdigest()[:16]


def lesson(topic_id: int) -> dict | None:
    t = db.session.get(Topic, topic_id)
    if t is None:
        return None
    subs = list(db.session.scalars(select(Subtopic).where(Subtopic.topic_id == t.id).order_by(Subtopic.position, Subtopic.id)))
    blocks = _blocks([s.id for s in subs])
    counts = dict(db.session.execute(select(Question.subtopic_id, func.count()).where(
        Question.subtopic_id.in_([s.id for s in subs]), Question.status != "archived").group_by(Question.subtopic_id)).all())
    return {"id": t.id, "section_id": t.section_id, "name": t.title, "minutes": t.est_minutes, "published": t.is_published,
            "rev": _rev(t, subs, blocks),
            "subs": [{"id": s.id, "name": s.title, "weight": s.weight, "generators": list(s.generators or []),
                      "questions": counts.get(s.id, 0),
                      "blocks": [{"id": b.id, "kind": b.kind, "data": _to_form(b.kind, b.data or {})} for b in blocks.get(s.id, [])]}
                     for s in subs]}


def _to_form(kind: str, d: dict) -> dict:
    """Bazadagi data → muharrir maydonlari (jadval — matn ko'rinishida, birinchi qator sarlavha)."""
    if kind == "table":
        rows = ([d["head"]] if d.get("head") else []) + (d.get("rows") or [])
        return {"title": d.get("title", ""), "body": "\n".join(" | ".join(str(c) for c in r) for r in rows), "head": bool(d.get("head"))}
    if kind == "links":
        return {"links": [{"title": x.get("title", ""), "url": x.get("url", "")} for x in d.get("links", [])]}
    if kind in EDITABLE:
        keys = {"text": ("title", "body"), "code": ("title", "code", "lang"), "image": ("src", "alt", "caption"),
                "mermaid": ("title", "code", "alt"), "formula": ("title", "tex"), "video": ("title", "url"),
                "callout": ("title", "body")}[kind]
        out = {k: d.get(k) or "" for k in keys}
        if kind == "callout" and not out["body"]:
            out["body"] = d.get("text") or ""
        return out
    return {"title": d.get("title", "")}


def _s(d: dict, key: str, limit: int = TEXT_MAX) -> str:
    v = d.get(key)
    return v.strip()[:limit] if isinstance(v, str) else ""


def _https(url: str, message: str) -> str:
    if not url.startswith("https://") or len(url) > 500 or re.search(r"\s", url):
        raise EditError(message)
    return url


def _clean(kind: str, d: dict, old: dict) -> dict:
    """Muharrir maydonlari → bazadagi data. Muharrirda yo'q kalitlar (masalan, svg) saqlanadi."""
    if kind == "table":
        rows = [[c.strip()[:500] for c in line.split("|")] for line in _s(d, "body").split("\n") if line.strip()][:60]
        if not rows:
            raise EditError(_("Jadval bo‘sh"))
        width = min(12, max(len(r) for r in rows))
        rows = [(r + [""] * width)[:width] for r in rows]
        out = {"rows": rows[1:], "head": rows[0]} if d.get("head") and len(rows) > 1 else {"rows": rows}
        return {**({"title": _s(d, "title", 200)} if _s(d, "title") else {}), **out}
    if kind == "links":
        links = [{"title": _s(x, "title", 200) or _s(x, "url", 200), "url": _https(_s(x, "url"), _("Havola https:// bilan boshlansin"))}
                 for x in (d.get("links") or [])[:20] if isinstance(x, dict) and (_s(x, "url") or _s(x, "title"))]
        if not links:
            raise EditError(_("Havola kiriting yoki blokni o‘chiring"))
        return {"links": links}
    need = {"text": "body", "code": "code", "image": "src", "mermaid": "code", "formula": "tex", "video": "url", "callout": "body"}[kind]
    out = {k: _s(d, k, CODE_MAX if k in ("code", "tex") else (TEXT_MAX if k == "body" else 300)) for k in _to_form(kind, {})}
    if kind in ("code", "mermaid"):                     # kodda boshidagi bo'sh joylar ahamiyatli
        out["code"] = (d.get("code") if isinstance(d.get("code"), str) else "").strip("\n")[:CODE_MAX]
    if not out[need].strip():
        raise EditError({"image": _("Rasmni yuklang"), "video": _("Video havolasini kiriting")}.get(kind, _("Blok bo‘sh")))
    if kind == "video":
        _https(out["url"], _("Video havolasi https:// bilan boshlansin"))
    if kind == "image":
        if not _IMG.fullmatch(out["src"]) or ".." in out["src"]:
            raise EditError(_("Rasmni qayta yuklang"))
        if not out["alt"]:
            raise EditError(_("Rasm tavsifini yozing (ko‘zi ojizlar uchun)"))
    out = {k: v for k, v in out.items() if v}
    keep = {k: v for k, v in old.items() if k not in _to_form(kind, {}) and k != "text"}
    if kind == "mermaid" and old.get("code") != out.get("code"):
        keep.pop("svg", None)                           # eski chizma yangi sxemaga mos emas
    return {**keep, **out}


def save_lesson(topic_id: int, payload: dict, actor_id: int) -> dict:
    """Darsni butunlay saqlaydi. Natija — lesson() ko'rinishi (yangi rev bilan). Xato — EditError / Conflict."""
    t = db.session.scalar(select(Topic).where(Topic.id == topic_id).with_for_update())
    if t is None:
        raise EditError(_("Dars topilmadi"))
    subs = {s.id: s for s in db.session.scalars(select(Subtopic).where(Subtopic.topic_id == t.id)
                                                .order_by(Subtopic.position, Subtopic.id))}
    blocks = _blocks(list(subs))
    if payload.get("rev") != _rev(t, subs.values(), blocks):
        raise Conflict(_("Dars orada boshqa joyda o‘zgartirilgan. Sahifani yangilab, o‘zgarishlaringizni qayta kiriting"))
    incoming = payload.get("subs")
    if not isinstance(incoming, list) or not incoming or not all(isinstance(x, dict) for x in incoming):
        raise EditError(_("Kamida bitta kichik mavzu bo‘lsin"))
    if len(incoming) > SUBS_MAX:
        raise EditError(_("Kichik mavzular juda ko‘p"))

    t.title = _name(payload.get("name"))
    _unique(Topic, Topic.section_id == t.section_id, t.title, t.id, _("Bu mavzuda bunday dars allaqachon bor"))
    m = payload.get("minutes")
    t.est_minutes = m if isinstance(m, int) and not isinstance(m, bool) and 1 <= m <= 600 else None
    names, keep_subs = set(), set()
    for pos, x in enumerate(incoming):
        name = _name(x.get("name"))
        if name.lower() in names:
            raise EditError(_("«%(n)s» kichik mavzusi ikki marta", n=name))
        names.add(name.lower())
        s = subs.get(x.get("id"))
        if s is None:
            s = Subtopic(topic_id=t.id, title=name, position=pos)
            db.session.add(s)
            db.session.flush()
        keep_subs.add(s.id)
        w = x.get("weight")
        s.title, s.position = name, pos
        s.weight = w if isinstance(w, int) and not isinstance(w, bool) and 0 <= w <= 50 else s.weight
        gens = x.get("generators") if isinstance(x.get("generators"), list) else []
        s.generators = [g for g in TEMPLATES if g in gens]
        _save_blocks(s, x.get("blocks"), {b.id: b for b in blocks.get(s.id, [])}, actor_id)
    for sid in subs.keys() - keep_subs:
        if _has_questions(Subtopic.id == sid):
            raise EditError(_("«%(n)s» kichik mavzusining savollari bor, o‘chirib bo‘lmaydi", n=subs[sid].title))
        db.session.execute(Subtopic.__table__.delete().where(Subtopic.id == sid))
        db.session.expunge(subs[sid])
    published = bool(payload.get("published"))
    if published and not t.is_published:
        db.session.flush()
        if not db.session.scalar(select(ContentBlock.id).join(Subtopic, Subtopic.id == ContentBlock.subtopic_id)
                                 .where(Subtopic.topic_id == t.id, ContentBlock.is_active.is_(True)).limit(1)) \
                and not _has_questions(Topic.id == t.id):
            raise EditError(_("Bo‘sh darsni nashr qilib bo‘lmaydi: blok yoki savol qo‘shing"))
    t.is_published = published
    _audit(actor_id, "update", "topic", t.id, {"title": t.title, "published": published})
    db.session.commit()
    return lesson(topic_id)


def _save_blocks(s: Subtopic, incoming, existing: dict[int, ContentBlock], actor_id: int) -> None:
    incoming = incoming if isinstance(incoming, list) else []
    if len(incoming) > BLOCKS_MAX:
        raise EditError(_("«%(n)s»: bloklar juda ko‘p", n=s.title))
    kept = set()
    for pos, x in enumerate(incoming):
        if not isinstance(x, dict):
            raise EditError(_("Blok noto‘g‘ri"))
        b = existing.get(x.get("id"))
        kind = b.kind if b is not None else x.get("kind")
        if b is not None and kind not in EDITABLE:      # muharrir bilmaydigan blok: faqat tartibi o'zgaradi
            b.position = pos
            kept.add(b.id)
            continue
        if kind not in EDITABLE:
            raise EditError(_("Blok turi noto‘g‘ri"))
        try:
            data = _clean(kind, x.get("data") if isinstance(x.get("data"), dict) else {}, (b.data or {}) if b is not None else {})
        except EditError as e:
            raise EditError(f"{s.title}, {pos + 1}-{_('blok')}: {e}") from None
        if b is None:
            b = ContentBlock(subtopic_id=s.id, kind=kind, position=pos, data=data, content_hash=_hash(kind, data), author_id=actor_id)
            db.session.add(b)
            db.session.flush()
        else:
            if data != b.data:
                b.data, b.version, b.content_hash = data, b.version + 1, _hash(kind, data)
            b.position = pos
        kept.add(b.id)
    for bid in existing.keys() - kept:
        db.session.delete(existing[bid])
