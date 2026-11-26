"""Oflayn paket: mavzuning darslari, rasmlari va oldindan tayyorlangan dars testlari (kalitsiz).

- Tayyor test — status = "offline" urinish: savollari band (boshqa testga tushmaydi), lekin «yakunlanmagan test» emas va
  «berilgan» ham emas. Birinchi javob serverga yetib kelganda boshlanadi (activate) va odatdagidek baholanadi.
- Onlayn shu dars testi boshlansa, o'sha tayyor test ishlatiladi: savol behuda sarflanmaydi.
- Paket o'chirilsa yoki KEEP_DAYS ichida ishlatilmasa, tayyor testlar o'chadi va savollari bankka qaytadi.
- Serverda fayl saqlanmaydi: sahifalar odatdagi manzillardan olinadi, brauzer ularni o'z keshiga yozadi (static/js/offline.js).
"""
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import current_app
from flask_babel import gettext as _
from sqlalchemy import delete, func, select

from ..extensions import db
from ..models import Question, TestAttempt
from . import attempts as at
from . import catalog, seen
from . import test_builder as tb
from .scoring import PASS_MIN

KEEP_DAYS, MAX_TOPICS = 30, 10
MAX_BYTES = 30 * 1024 * 1024
_IMG = re.compile(r"(uploads|img)/[\w./-]+\.(png|jpg|jpeg|webp|svg)")


class OfflineError(ValueError):
    pass


def _lock(user_id: int) -> None:
    db.session.execute(select(func.pg_advisory_xact_lock(6, int(user_id) % 2_147_483_647)))     # tb.get_or_start bilan bitta navbat


def reserved(user_id: int, subtopic_id: int) -> TestAttempt | None:
    """Shu darsning tayyor testi; savoli bankdan olingan bo'lsa (arxiv, to'xtatilgan) — o'chiriladi. Commit qilmaydi."""
    a = db.session.scalar(select(TestAttempt).where(TestAttempt.user_id == user_id, TestAttempt.status == "offline",
                                                    TestAttempt.subtopic_id == subtopic_id).with_for_update())
    if a is None:
        return None
    ids = [i.question_id for i in a.items]
    ok = db.session.scalar(select(func.count()).select_from(Question).where(Question.id.in_(ids), Question.status == "approved"))
    if ok == len(ids) and ids:
        return a
    db.session.delete(a)
    db.session.flush()
    return None


def activate(a: TestAttempt) -> TestAttempt:
    """Tayyor testni boshlaydi (a — qulflangan qator). Commit qilmaydi."""
    if a.status == "offline":
        now = datetime.now(timezone.utc)
        a.status, a.started_at = "in_progress", now
        a.deadline_at = now + timedelta(seconds=a.settings_snapshot.get("seconds") or 0)
        seen.mark(a.user_id, [i.question_id for i in a.items])
        db.session.flush()
    return a


def _tests(user_id: int, topic_id: int, lessons: list[dict]) -> dict[int, TestAttempt]:
    """{dars: urinish} — hali o'zlashtirilmagan darslar uchun. Savol yetmagan dars testsiz qoladi."""
    scores = catalog.lesson_scores(user_id, topic_id)
    started = {a.subtopic_id: a for a in tb.unfinished(user_id) if a.kind == "lesson" and a.topic_id == topic_id}
    out = {}
    for x in lessons:
        sid = x["id"]
        if not x["testable"] or scores.get(sid, 0) >= PASS_MIN:
            continue
        a = started.get(sid) or reserved(user_id, sid)
        if a is None:
            try:
                spec = tb.build(user_id, "lesson", subtopic_id=sid)
            except tb.Unavailable:
                continue
            a = at.create(user_id, spec, status="offline")
        out[sid] = a
    return out


def topics(user_id: int) -> set[int]:
    """Paketi bor mavzular (tayyor testi bor)."""
    return set(db.session.scalars(select(TestAttempt.topic_id).where(TestAttempt.user_id == user_id, TestAttempt.status == "offline")))


def build(user_id: int, topic_id: int) -> dict:
    """Paket tarkibi. Commit qiladi."""
    lesson = catalog.lesson_view(topic_id)
    if lesson is None or not lesson["parts"]:
        raise OfflineError(_("Bu mavzuning darsi hali tayyor emas"))
    _lock(user_id)
    if len(topics(user_id) - {topic_id}) >= MAX_TOPICS:
        raise OfflineError(_("Ko‘pi bilan %(n)s ta mavzu yuklab olinadi. Keraksizini o‘chiring", n=MAX_TOPICS))
    lessons = catalog.lessons_by_topic(topic_id).get(topic_id, [])
    tests = _tests(user_id, topic_id, lessons)
    images = _images(lesson, tests.values())
    total = sum(size for _path, size in images)
    if total > MAX_BYTES:
        db.session.rollback()
        raise OfflineError(_("Paket 30 MB dan katta: rasmlari ko‘p"))
    db.session.commit()
    return {"name": lesson["name"], "tests": {sid: str(a.client_uuid) for sid, a in tests.items()},
            "images": [p for p, _size in images], "bytes": total, "lessons": len(lesson["parts"])}


def _images(lesson: dict, attempts) -> list[tuple[str, int]]:
    """Dars bloklari va savollardagi rasmlar: [(static'ga nisbatan yo'l, hajmi)]. Fayli yo'qlari kirmaydi."""
    found = [b["data"].get("src") for p in lesson["parts"] for b in p["blocks"]]
    for a in attempts:
        for snap, _sid, _tid in at._snapshots(a).values():
            found.append(((snap.get("data") or {}).get("image") or {}).get("src"))
    root, out = Path(current_app.static_folder), {}
    for src in found:
        if isinstance(src, str) and _IMG.fullmatch(src) and ".." not in src and (root / src).is_file():
            out[src] = (root / src).stat().st_size
    return sorted(out.items())


def page_tests(user_id: int, topic_id: int) -> dict[int, str]:
    """{dars: urinish uuid} — paket sahifasi uchun (yangi test tuzmaydi)."""
    rows = db.session.execute(select(TestAttempt.subtopic_id, TestAttempt.client_uuid).where(
        TestAttempt.user_id == user_id, TestAttempt.topic_id == topic_id, TestAttempt.kind == "lesson",
        TestAttempt.status.in_(("offline", "in_progress"))))
    return {sid: str(u) for sid, u in rows}


def release(user_id: int, topic_id: int) -> int:
    """Paket o'chirildi: boshlanmagan tayyor testlar o'chadi. Commit qiladi."""
    _lock(user_id)
    n = db.session.execute(delete(TestAttempt).where(TestAttempt.user_id == user_id, TestAttempt.topic_id == topic_id,
                                                     TestAttempt.status == "offline").execution_options(synchronize_session=False)).rowcount
    db.session.commit()
    return n


def purge() -> int:
    """KEEP_DAYS dan eski tayyor testlar (fon vazifasi). Commit qilmaydi."""
    return db.session.execute(delete(TestAttempt).where(
        TestAttempt.status == "offline", TestAttempt.started_at < datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS))
        .execution_options(synchronize_session=False)).rowcount
