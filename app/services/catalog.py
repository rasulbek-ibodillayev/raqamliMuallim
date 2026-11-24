"""Kontent katalogi: bo'limlar, mavzular, kichik mavzular va dars bloklari — foydalanuvchi progressi bilan.

Ko'rinishlar shablonlarga oddiy dict'lar beradi (ORM obyektlari emas): shablon bazaga qo'shimcha so'rov yubormaydi.
"""
from sqlalchemy import func, select

from ..extensions import db
from ..models import (AttemptItem, ContentBlock, ErrorItem, Question, Section, Subtopic, TestAttempt, Topic,
                      UserTopicProgress)
from .archive import rows as rows_of
from .archive import unpack
from .timefmt import when

SOLID_MIN = 90
PASS_PCT = 70   # kichik mavzu «tayyor» chegarasi (mavzu ochilish chegarasi bilan bir xil, TZ 7)


def topic_titles() -> list[dict]:
    """Barcha nashr qilingan mavzular, bo'lim tartibida: [{"id", "name", "section"}]. Qidiruv va eslatmalar uchun."""
    rows = db.session.execute(
        select(Topic.id, Topic.title, Section.title)
        .join(Section, Topic.section_id == Section.id)
        .where(Topic.is_published.is_(True))
        .order_by(Section.position, Section.id, Topic.position, Topic.id)
    ).all()
    return [{"id": tid, "name": name, "section": sec} for tid, name, sec in rows]


def lessons_by_topic(topic_id: int | None = None) -> dict[int, list[dict]]:
    """{mavzu: [{"id", "name", "has_blocks", "testable"}]} — mavzuning darslari tartib bilan.

    Dars — bloklari bor kichik mavzu; mavzuda bloklar umuman bo'lmasa — savollari bor kichik mavzular.
    testable — tasdiqlangan savoli bor (dars testini topshirish mumkin)."""
    blocks = select(ContentBlock.id).where(ContentBlock.subtopic_id == Subtopic.id, ContentBlock.is_active.is_(True),
                                           ContentBlock.kind != "example").exists()
    asks = select(Question.id).where(Question.subtopic_id == Subtopic.id, Question.status == "approved").exists()
    q = select(Subtopic.topic_id, Subtopic.id, Subtopic.title, blocks, asks).order_by(Subtopic.position, Subtopic.id)
    if topic_id is not None:
        q = q.where(Subtopic.topic_id == topic_id)
    subs: dict[int, list[dict]] = {}
    for tid, sid, name, b, a in db.session.execute(q):
        subs.setdefault(tid, []).append({"id": sid, "name": name, "has_blocks": b, "testable": a})
    return {tid: ([x for x in xs if x["has_blocks"]] or [x for x in xs if x["testable"]]) for tid, xs in subs.items()}


def diagnostic_estimate() -> tuple[int, int]:
    """(to'liq rejadagi darslar soni, diagnostika daqiqasi): har darsga 60 soniya (TZ; Tuzatish 4–5)."""
    published = set(db.session.scalars(select(Topic.id).where(Topic.is_published.is_(True))))
    n = sum(len(xs) for tid, xs in lessons_by_topic().items() if tid in published)
    return n, n


def error_items(user_id: int, limit: int = 50) -> tuple[list[dict], int]:
    """Tuzatilmagan xatolar, yangisi birinchi: ([{"q", "section", "meta", "rep", "rid"}], jami soni)."""
    base = select(ErrorItem).where(ErrorItem.user_id == user_id, ErrorItem.resolved_at.is_(None))
    total = db.session.scalar(select(func.count()).select_from(base.subquery()))
    # «Qayta xato»: savol takrorlanmaydi, shuning uchun shu kichik mavzuda nechta testda xato qilingani sanaladi
    times = (select(ErrorItem.subtopic_id, func.count(ErrorItem.last_attempt_id.distinct()).label("n"))
             .where(ErrorItem.user_id == user_id, ErrorItem.resolved_at.is_(None)).group_by(ErrorItem.subtopic_id).subquery())
    rows = db.session.execute(
        select(Question.text, Subtopic.title, Topic.title, func.greatest(times.c.n, 1), ErrorItem.last_wrong_at,
               ErrorItem.last_attempt_id)
        .join(times, times.c.subtopic_id == ErrorItem.subtopic_id)
        .join(Question, Question.id == ErrorItem.question_id).join(Subtopic, Subtopic.id == ErrorItem.subtopic_id)
        .join(Topic, Topic.id == Subtopic.topic_id)
        .where(ErrorItem.user_id == user_id, ErrorItem.resolved_at.is_(None))
        .order_by(ErrorItem.last_wrong_at.desc(), ErrorItem.id.desc()).limit(limit)).all()
    return [{"q": text, "section": f"{top} · {sub}", "rep": n > 1, "when": when(at_), "wrong": n, "rid": rid}
            for text, sub, top, n, at_, rid in rows], total


def lesson_scores(user_id: int, topic_id: int) -> dict[int, int]:
    """{kichik mavzu: dars testining eng yaxshi foizi}. Keyingi dars shunga qarab ochiladi; qayta o'zlashtirib
    ≥ 90% qilinsa, dars tavsiya ro'yxatidan chiqadi."""
    rows = db.session.execute(
        select(TestAttempt.subtopic_id, func.max(TestAttempt.score_pct))
        .where(TestAttempt.user_id == user_id, TestAttempt.topic_id == topic_id, TestAttempt.kind == "lesson",
               TestAttempt.status == "submitted", TestAttempt.subtopic_id.is_not(None))
        .group_by(TestAttempt.subtopic_id)).all()
    return {sid: int(pct) for sid, pct in rows}


def lesson_result_ids(user_id: int, topic_id: int) -> dict[int, int]:
    """{kichik mavzu: eng yaxshi dars testi urinishining id'si} — dars sahifasidagi natija havolasi uchun."""
    rows = db.session.execute(
        select(TestAttempt.subtopic_id, TestAttempt.id)
        .where(TestAttempt.user_id == user_id, TestAttempt.topic_id == topic_id, TestAttempt.kind == "lesson",
               TestAttempt.status == "submitted", TestAttempt.subtopic_id.is_not(None))
        .distinct(TestAttempt.subtopic_id)
        .order_by(TestAttempt.subtopic_id, TestAttempt.score_pct.desc(), TestAttempt.id.desc())).all()
    return dict(tuple(r) for r in rows)


def recommended_lessons(user_id: int) -> list[dict]:
    """Tavsiya bilan (70–89%) o'tilgan darslar — bosh sahifa va «Xatolar analitikasi»da:
    - dars testining eng yaxshi natijasi 70–89%;
    - bosqichli testda mavzusi 70–89% bilan o'tgan, o'zi 90% ga yetmagan darslar (ixtiyoriy testdan tashqari —
      u o'quv rejaga ta'sir qilmaydi).
    Keyin dars testi ≥ 90% topshirilsa, dars ro'yxatdan chiqadi. Yangisi birinchi."""
    rows = db.session.execute(
        select(TestAttempt.id, TestAttempt.kind, TestAttempt.subtopic_id, TestAttempt.score_pct, TestAttempt.finished_at,
               TestAttempt.settings_snapshot["recommended"])
        .where(TestAttempt.user_id == user_id, TestAttempt.status == "submitted", TestAttempt.kind != "optional")
        .order_by(TestAttempt.finished_at, TestAttempt.id)).all()
    found: dict[int, dict] = {}
    best: dict[int, float] = {}
    for aid, kind, sid, pct, at_, rec in rows:
        if kind == "lesson" and sid:
            if pct >= SOLID_MIN:
                found.pop(sid, None)
            elif pct >= PASS_PCT and pct >= best.get(sid, 0):
                found[sid] = {"pct": int(pct), "rid": aid, "at": at_}
            best[sid] = max(best.get(sid, 0), pct)
        for s, p in (rec or {}).items():
            found[int(s)] = {"pct": p, "rid": aid, "at": at_}
    if not found:
        return []
    info = db.session.execute(
        select(Subtopic.id, Subtopic.title, Topic.id, Topic.title, select(ContentBlock.id).where(
            ContentBlock.subtopic_id == Subtopic.id, ContentBlock.is_active.is_(True)).exists())
        .join(Topic, Topic.id == Subtopic.topic_id).where(Subtopic.id.in_(found), Topic.is_published.is_(True))).all()
    out = [{**found[sid], "sid": sid, "lesson": name, "topic_id": tid, "topic": topic, "has_lesson": blocks,
            "when": when(found[sid]["at"])} for sid, name, tid, topic, blocks in info]
    return sorted(out, key=lambda r: r["at"], reverse=True)


def subtopic_scores(user_id: int, topic_id: int) -> dict[int, int]:
    """Foydalanuvchining shu mavzu kichik mavzularidagi o'rtacha bali (0–100): yakunlangan testlar bo'yicha,
    ixtiyoriy testlarsiz (ular o'zlashtirish foiziga ta'sir qilmaydi)."""
    mine = (TestAttempt.user_id == user_id, TestAttempt.status == "submitted", TestAttempt.kind != "optional")
    acc = {sid: [int(total), n] for sid, total, n in db.session.execute(
        select(Question.subtopic_id, func.sum(AttemptItem.score), func.count())
        .join(AttemptItem, AttemptItem.question_id == Question.id)
        .join(TestAttempt, TestAttempt.id == AttemptItem.attempt_id)
        .join(Subtopic, Subtopic.id == Question.subtopic_id)
        .where(*mine, Subtopic.topic_id == topic_id, AttemptItem.score.is_not(None))
        .group_by(Question.subtopic_id))}
    old = db.session.scalars(select(TestAttempt.items_archive).where(*mine, TestAttempt.items_archive.is_not(None),
                                                                     func.coalesce(TestAttempt.topic_id, topic_id) == topic_id)).all()
    if old:
        sub_of = dict(db.session.execute(select(Question.id, Question.subtopic_id).join(Subtopic)
                                         .where(Subtopic.topic_id == topic_id)).all())
        for i in (i for blob in old for i in unpack(blob)):
            if i.score is not None and i.question_id in sub_of:
                s = acc.setdefault(sub_of[i.question_id], [0, 0])
                s[0] += i.score
                s[1] += 1
    return {sid: round(total / n) for sid, (total, n) in acc.items()}


def optional_topics(user_id: int) -> list[dict]:
    """Ixtiyoriy test uchun mavzular: tasdiqlangan savollari bor, nashr qilingan; o'zlashtirilganlari belgilangan.
    Hali hech biri o'zlashtirilmagan bo'lsa — hammasi belgilangan."""
    rows = db.session.execute(
        select(Topic.id, Topic.title, func.count(Question.id), func.coalesce(UserTopicProgress.status, "none"))
        .join(Section, Section.id == Topic.section_id)
        .join(Subtopic, Subtopic.topic_id == Topic.id).join(Question, Question.subtopic_id == Subtopic.id)
        .outerjoin(UserTopicProgress, (UserTopicProgress.topic_id == Topic.id) & (UserTopicProgress.user_id == user_id))
        .where(Topic.is_published.is_(True), Question.status == "approved", Subtopic.weight > 0)
        .group_by(Topic.id, Section.id, UserTopicProgress.status)
        .order_by(Section.position, Section.id, Topic.position, Topic.id)).all()
    any_done = any(st in ("done", "solid") for *_x, st in rows)
    return [{"id": tid, "name": name, "n": n, "status": st, "on": st in ("done", "solid") or not any_done}
            for tid, name, n, st in rows]


def attempt_by_section(a: TestAttempt) -> list[dict]:
    """Urinish natijasi bo'limlar bo'yicha: [{"name", "pct", "topics", "known"}] (known — ≥ 90% chiqqan mavzular)."""
    from .attempts import dropped
    gone = dropped(a)
    items = [i for i in rows_of(a) if i.position not in gone]
    where = {qid: (sid, name, tid) for qid, sid, name, tid in db.session.execute(
        select(Question.id, Section.id, Section.title, Topic.id).join(Subtopic, Subtopic.id == Question.subtopic_id)
        .join(Topic, Topic.id == Subtopic.topic_id).join(Section, Section.id == Topic.section_id)
        .where(Question.id.in_([i.question_id for i in items]))
        .order_by(Section.position, Section.id, Topic.position))}
    score = {i.question_id: i.score or 0 for i in items}
    topics: dict[tuple, list[int]] = {}
    for qid, at_ in where.items():                                  # bo'lim va mavzu tartibida
        topics.setdefault(at_, []).append(score[qid])
    out: dict[int, dict] = {}
    for (sid, name, _tid), scores in topics.items():
        s = out.setdefault(sid, {"name": name, "sum": 0, "n": 0, "topics": 0, "known": 0})
        s["sum"] += sum(scores)
        s["n"] += len(scores)
        s["topics"] += 1
        s["known"] += sum(scores) / len(scores) >= SOLID_MIN
    return [{"name": s["name"], "pct": round(s["sum"] / s["n"]), "topics": s["topics"], "known": s["known"]}
            for s in out.values()]


def topic_view(topic_id: int, user_id: int) -> dict | None:
    """Mavzu sahifasi uchun: nomi, bo'limi, holati, eng yaxshi natija, kichik mavzular (foizi bilan) va eng zaif qism."""
    row = db.session.execute(
        select(Topic, Section.title).join(Section, Topic.section_id == Section.id)
        .where(Topic.id == topic_id, Topic.is_published.is_(True))
    ).first()
    if row is None:
        return None
    topic, section = row
    progress = db.session.get(UserTopicProgress, (user_id, topic_id))
    scores = subtopic_scores(user_id, topic_id)
    subs = db.session.execute(select(Subtopic.id, Subtopic.title).where(Subtopic.topic_id == topic_id)
                              .order_by(Subtopic.position, Subtopic.id)).all()
    subtopics = [{"id": sid, "name": title, "pct": scores.get(sid)} for sid, title in subs]
    scored = [s for s in subtopics if s["pct"] is not None]
    weak = min((s for s in scored if s["pct"] < PASS_PCT), key=lambda s: s["pct"], default=None)
    return {
        "id": topic.id, "name": topic.title, "section": section,
        "status": progress.status if progress else "none",
        "best_pct": round(progress.best_pct) if progress and progress.best_pct is not None else None,
        "lesson_pct": progress.lesson_pct if progress else 0,
        "subtopics": subtopics, "scored": len(scored),
        "ready": sum(1 for s in scored if s["pct"] >= PASS_PCT), "weak": weak,
        "has_blocks": db.session.scalar(select(func.count()).select_from(ContentBlock).join(Subtopic)
                                        .where(Subtopic.topic_id == topic_id, ContentBlock.is_active.is_(True))) > 0,
    }


def lesson_view(topic_id: int) -> dict | None:
    """Dars: mavzu va kichik mavzular, har birida faol bloklar tartib bo'yicha. Bloklarsiz kichik mavzu ko'rsatilmaydi."""
    row = db.session.execute(
        select(Topic.id, Topic.title, Section.title).join(Section, Topic.section_id == Section.id)
        .where(Topic.id == topic_id, Topic.is_published.is_(True))
    ).first()
    if row is None:
        return None
    blocks = db.session.execute(
        select(Subtopic.id, Subtopic.title, ContentBlock.id, ContentBlock.kind, ContentBlock.data, ContentBlock.audio_text)
        .join(ContentBlock, ContentBlock.subtopic_id == Subtopic.id)
        .where(Subtopic.topic_id == topic_id, ContentBlock.is_active.is_(True), ContentBlock.kind != "example")
        .order_by(Subtopic.position, Subtopic.id, ContentBlock.position, ContentBlock.id)
    ).all()
    parts: dict[int, dict] = {}
    for sid, stitle, bid, kind, data, audio in blocks:
        part = parts.setdefault(sid, {"id": sid, "anchor": f"k{sid}", "name": stitle, "blocks": []})
        part["blocks"].append({"id": bid, "kind": kind, "data": data or {}, "audio_text": audio})
    return {"id": row[0], "name": row[1], "section": row[2], "parts": list(parts.values())}
