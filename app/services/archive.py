"""Yakunlangan testlar arxivi: 7 kundan keyin attempt_items qatorlari → test_attempts.items_archive (ixcham ikkilik).

Natija o'chmaydi va sifati pasaymaydi: natija sahifasi, yechim, e'tiroz, kichik mavzu foizlari va qayta hisoblash arxivdan
ham o'qiydi (rows). Savol matni arxivga tushmaydi — u questions / question_versions'da.

Nega o'z formatimiz (1 mln javob = 50 000 test × 20, o'lchandi): jadvalda 110 MB, shu formatda ≈ 6 MB. Solishtirish: DuckDB
10 MB (+32 MB RAM), SQLite 20 MB, CSV 28 MB; 20 savollik test JSON + zlib 202, MessagePack + zlib 133, shu format 124 bayt.

Muddat o'tgani foydalanuvchi yangi test boshlaganda siqiladi (compress_user) — fon vazifasi shart emas. Hammasi uchun:
`flask eski-testlarni-siqish`.

Bayt tartibi: har savol uchun varint savol id, varint versiya, varint (soniya + 1; 0 — noma'lum), ball (255 — NULL), javob.
Javob: 0–99 — indeks; 100 — yo'q; 101 — ro'yxat (uzunlik, elementlar; 255 — bo'sh); 102 — matn; 103 — boshqa (JSON).
Tartib raqami — navbati.
"""
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy import LargeBinary, delete, func, literal, select

from ..extensions import db
from ..models import AttemptItem, TestAttempt

AFTER_DAYS = 7
BATCH = 200
NO_SCORE, A_NONE, A_LIST, A_TEXT, A_JSON = 255, 100, 101, 102, 103


def _varint(n: int) -> bytes:
    out = bytearray()
    while n > 127:
        out.append(n & 127 | 128)
        n >>= 7
    out.append(n)
    return bytes(out)


def _small(v, limit: int) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and 0 <= v < limit


def _answer(v) -> bytes:
    if v is None:
        return bytes((A_NONE,))
    if _small(v, A_NONE):
        return bytes((v,))
    if isinstance(v, list) and len(v) < 256 and all(x is None or _small(x, 255) for x in v):
        return bytes((A_LIST, len(v), *(255 if x is None else x for x in v)))
    tag, raw = (A_TEXT, v.encode()) if isinstance(v, str) else (A_JSON, json.dumps(v, ensure_ascii=False).encode())
    return bytes((tag,)) + _varint(len(raw)) + raw


def pack(items) -> bytes:
    """items — tartib bo'yicha (0, 1, 2 …)."""
    out = bytearray()
    for n, i in enumerate(items):
        if i.position != n:
            raise ValueError("savollar tartibi uzluksiz emas")
        out += _varint(i.question_id) + _varint(i.question_version)
        out += _varint(0 if i.time_ms is None else round(i.time_ms / 1000) + 1)
        out.append(NO_SCORE if i.score is None else i.score)
        out += _answer((i.answer or {}).get("v"))
    return bytes(out)


def scan(blob: bytes):
    """Tez o'qish: (savol id, versiya, soniya + 1, ball, javob) — obyekt yaratmaydi (foizlarni hisoblash uchun)."""
    at, end = 0, len(blob)
    while at < end:
        nums = []
        for _ in (0, 1, 2):
            b = blob[at]
            at += 1
            n = b & 127
            shift = 7
            while b > 127:
                b = blob[at]
                at += 1
                n |= (b & 127) << shift
                shift += 7
            nums.append(n)
        score, v = blob[at], blob[at + 1]
        at += 2
        if v >= A_NONE:
            if v == A_NONE:
                v = None
            elif v == A_LIST:
                n = blob[at]
                v = [None if x == 255 else x for x in blob[at + 1:at + 1 + n]]
                at += 1 + n
            else:
                tag, n, shift = v, 0, 0
                while True:
                    b = blob[at]
                    at += 1
                    n |= (b & 127) << shift
                    shift += 7
                    if b < 128:
                        break
                raw = blob[at:at + n].decode()
                v = raw if tag == A_TEXT else json.loads(raw)
                at += n
        yield nums[0], nums[1], nums[2], None if score == NO_SCORE else score, v


def unpack(blob: bytes) -> list[SimpleNamespace]:
    return [SimpleNamespace(position=n, question_id=qid, question_version=ver, time_ms=(sec - 1) * 1000 if sec else None,
                            score=score, answer=None if v is None else {"v": v})
            for n, (qid, ver, sec, score, v) in enumerate(scan(blob))]


def rows(a: TestAttempt) -> list:
    """Urinishdagi savollar, tartib bilan: bazadagi qatorlar yoki (arxivlangan bo'lsa) arxivdan, faqat o'qish uchun."""
    return unpack(a.items_archive) if a.items_archive is not None else a.items


def may_have(question_id: int):
    """SQL sharti: arxivda shu savol bo'lishi mumkin (id baytlari uchraydi). Aniq tekshiruv — unpack'dan keyin."""
    needle = literal(_varint(question_id), LargeBinary)
    return func.position(needle.op("IN")(TestAttempt.items_archive)) > 0


def _compress(where, limit: int) -> int:
    batch = list(db.session.scalars(
        select(TestAttempt).where(TestAttempt.status == "submitted", TestAttempt.items_archive.is_(None), *where,
                                  TestAttempt.items.any())
        .order_by(TestAttempt.id).limit(limit).with_for_update(skip_locked=True)))
    for a in batch:
        a.items_archive = pack(a.items)
    db.session.flush()
    if batch:
        db.session.execute(delete(AttemptItem).where(AttemptItem.attempt_id.in_([a.id for a in batch]))
                           .execution_options(synchronize_session=False))
        for a in batch:
            db.session.expire(a, ["items"])
    return len(batch)


def _before(now: datetime | None = None, days: int = AFTER_DAYS) -> datetime:
    return (now or datetime.now(timezone.utc)) - timedelta(days=days)


def compress_user(user_id: int) -> int:
    """Foydalanuvchining muddati o'tgan testlari (ko'pi bilan 20 ta). Commit qilmaydi."""
    return _compress((TestAttempt.user_id == user_id, TestAttempt.finished_at < _before()), 20)


def compress_old(now: datetime | None = None, days: int = AFTER_DAYS) -> int:
    """Hamma foydalanuvchilar: BATCH tadan commit qiladi. Natija: siqilgan urinishlar soni."""
    done = 0
    while n := _compress((TestAttempt.finished_at < _before(now, days),), BATCH):
        db.session.commit()
        done += n
    return done
