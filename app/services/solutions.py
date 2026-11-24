"""«Yechimini ko'rish»: yakunlangan testdagi savolning yechimi — AI tutor suhbatida ko'rsatiladi.

Hozir yechim bazadan tuziladi: to'g'ri javob, izoh (explanation) va har bir variantning izohi (answer.notes). Shablon
savollarda izohni hisob-kitob bilan shablonning o'zi yozadi.

13-bosqichda AI shu yerga ulanadi. Yechim foydalanuvchiga emas, savolga bog'liq: ai_cache (kind="solve", kalit — savol id va
versiyasi), ya'ni bitta savol uchun model bir marta chaqiriladi. Modelga foydalanuvchi haqida hech narsa yuborilmaydi.
Ko'rsatma: hisoblash savolida — yechish usuli qadam-baqadam; nazariy savolda — har bir javob izohi va to'g'ri javobning
nega to'g'riligi isboti. Javob bazadagi kalitga zid bo'lsa, ko'rsatilmaydi (ekspertga xabar).
"""
import uuid as uuidlib

from sqlalchemy import select

from ..extensions import db
from ..models import ContentBlock
from . import attempts as at


def for_attempt(user_id: int, attempt_uuid: uuidlib.UUID, pos: int) -> tuple[dict, tuple[int, int] | None] | None:
    """(savol tahlili — attempts.review qatori, (mavzu, kichik mavzu) — darsi bo'lsa) yoki None.

    Faqat o'zining yakunlangan testi: test davomida (bosqichlar orasida ham) kalit oshkor bo'lmaydi."""
    a = at.get(attempt_uuid)
    if a is None or a.user_id != user_id or a.status != "submitted":
        return None
    r = next((x for x in at.review(a) if x["pos"] == pos), None)
    if r is None:
        return None
    _snap, sid, tid = at._snapshots(a)[pos]
    has_lesson = db.session.scalar(select(ContentBlock.id).where(
        ContentBlock.subtopic_id == sid, ContentBlock.is_active.is_(True), ContentBlock.kind != "example").limit(1))
    return r, ((tid, sid) if has_lesson else None)
