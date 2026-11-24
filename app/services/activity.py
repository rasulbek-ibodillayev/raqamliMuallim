"""Kunlik faollik: har foydalanuvchi uchun kuniga bir marta last_seen_at yangilanadi va daily_stats'ga qo'shiladi.

last_seen_at faqat kirishda emas, har kuni yangilanadi: «eslab qolish» bilan kirib yurgan odam 6 oylik o'chirishga tushmaydi.
daily_stats — kuniga bitta qator (kim kirgani yozilmaydi).
"""
from datetime import datetime, timezone

from sqlalchemy import or_, update
from sqlalchemy.dialects.postgresql import insert

from ..extensions import db
from ..models import DailyStat, User
from .timefmt import TASHKENT, now


def device(user_agent: str) -> str:
    ua = user_agent.lower()
    if "ipad" in ua or "tablet" in ua or ("android" in ua and "mobile" not in ua):
        return "tablet"
    return "phone" if "mobi" in ua or "iphone" in ua or "android" in ua else "desktop"


def touch(user: User, user_agent: str = "", pwa: bool = False) -> bool:
    """Bugun birinchi so'rov bo'lsa yozadi va commit qiladi. Parallel so'rovlarda ham bir marta sanaladi."""
    today = now().date()
    if user.last_seen_at is not None and user.last_seen_at.astimezone(TASHKENT).date() >= today:
        return False
    start = datetime.combine(today, datetime.min.time(), TASHKENT)
    first = db.session.execute(
        update(User).where(User.id == user.id, or_(User.last_seen_at.is_(None), User.last_seen_at < start))
        .values(last_seen_at=datetime.now(timezone.utc), updated_at=User.updated_at)
        .execution_options(synchronize_session="fetch")).rowcount
    if first and user.role == "user":
        kind = device(user_agent)
        add = {"active": 1, "phone": int(kind == "phone"), "tablet": int(kind == "tablet"), "pwa": int(pwa)}
        stmt = insert(DailyStat).values(day=today, **add)
        db.session.execute(stmt.on_conflict_do_update(index_elements=[DailyStat.day], set_={
            k: getattr(DailyStat, k) + stmt.excluded[k] for k in add}))
    db.session.commit()
    return bool(first)
