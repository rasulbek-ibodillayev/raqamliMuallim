"""12 oydan eski urinishlar arxivi: attempt_items qatorlari → test_attempts.items_archive (zlib + JSON).

Natija o'chmaydi: natija sahifasi, e'tiroz va kichik mavzu foizlari arxivdan ham o'qiydi (rows). Savol matni arxivga
tushmaydi — u question_versions'da turadi. Buyruq: `flask eski-testlarni-siqish` (10-bosqichda fon vazifasi bo'ladi).
"""
import json
import zlib
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy import delete, select

from ..extensions import db
from ..models import AttemptItem, TestAttempt

AFTER_DAYS = 365
BATCH = 200


def pack(items) -> bytes:
    """Ustunlar bo'yicha (tartib, savol, versiya, vaqt, ball, javob): qatorlardan yaxshiroq siqiladi."""
    cols = list(zip(*((i.position, i.question_id, i.question_version, i.time_ms, i.score,
                       (i.answer or {}).get("v")) for i in items)))
    return zlib.compress(json.dumps(cols, ensure_ascii=False, separators=(",", ":")).encode(), 9)


def unpack(blob: bytes) -> list[SimpleNamespace]:
    cols = json.loads(zlib.decompress(blob))
    return [SimpleNamespace(position=p, question_id=q, question_version=ver, time_ms=ms, score=score,
                            answer=None if v is None else {"v": v}) for p, q, ver, ms, score, v in zip(*cols)]


def rows(a: TestAttempt) -> list:
    """Urinishdagi savollar, tartib bilan: bazadagi qatorlar yoki (arxivlangan bo'lsa) arxivdan, faqat o'qish uchun."""
    return unpack(a.items_archive) if a.items_archive is not None else a.items


def compress_old(now: datetime | None = None, days: int = AFTER_DAYS) -> int:
    """Muddati o'tgan urinishlarni siqadi, BATCH tadan commit qiladi. Natija: siqilgan urinishlar soni."""
    before = (now or datetime.now(timezone.utc)) - timedelta(days=days)
    done = 0
    while True:
        batch = list(db.session.scalars(
            select(TestAttempt).where(TestAttempt.status == "submitted", TestAttempt.finished_at < before,
                                      TestAttempt.items_archive.is_(None), TestAttempt.items.any())
            .order_by(TestAttempt.id).limit(BATCH).with_for_update(skip_locked=True)))
        if not batch:
            return done
        for a in batch:
            a.items_archive = pack(a.items)
        db.session.flush()
        ids = [a.id for a in batch]
        db.session.execute(delete(AttemptItem).where(AttemptItem.attempt_id.in_(ids))
                           .execution_options(synchronize_session=False))
        db.session.commit()
        db.session.expire_all()
        done += len(ids)
