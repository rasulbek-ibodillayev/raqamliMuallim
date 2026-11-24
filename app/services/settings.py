"""Admin sozlamalari (settings jadvali): faqat standartdan farqli qiymat saqlanadi.

O'zgarish yangi boshlangan testlarga ta'sir qiladi (urinish o'z savollari va vaqtini saqlaydi). O'tish chegaralari (70 / 90),
dars testi (3 savol), oraliq sinov (har 3 mavzu) va 6 oylik muddat bu yerda emas: ular tasdiqlangan qoida, maxfiylik siyosati
va barcha matnlarda shunday yozilgan.
"""
from dataclasses import dataclass

from flask import g, has_app_context
from flask_babel import lazy_gettext as _l
from sqlalchemy import select

from ..extensions import db
from ..models import Setting


@dataclass(frozen=True)
class Item:
    default: int
    low: int
    high: int
    group: str
    label: object
    hint: object
    unit: object = ""


ITEMS: dict[str, Item] = {
    "daily_n": Item(5, 3, 20, "count", _l("Kunlik test"), _l("Savollar soni"), _l("savol")),
    "weekly_n": Item(20, 10, 60, "count", _l("Haftalik test"), _l("Savollar soni (bosqichlarga teng bo‘linadi)"), _l("savol")),
    "monthly_n": Item(30, 10, 90, "count", _l("Oylik test"), _l("Savollar soni (bosqichlarga teng bo‘linadi)"), _l("savol")),
    "exam_n": Item(35, 10, 100, "count", _l("Attestatsiya testi"), _l("Savollar soni"), _l("savol")),
    "exam_minutes": Item(120, 10, 300, "count", _l("Attestatsiya testi vaqti"), _l("Umumiy vaqt"), _l("daqiqa")),
    "monthly_days": Item(30, 14, 90, "plan", _l("Oylik test oralig‘i"), _l("Oxirgi oylik testdan keyin shuncha kun o‘tgach navbati keladi"), _l("kun")),
    "pace_days": Item(2, 1, 14, "plan", _l("Bitta mavzuga"), _l("Attestatsiya sanasi kiritilmagan bo‘lsa, reja shu sur’atda tuziladi"), _l("kun")),
    "reserve_days": Item(3, 0, 30, "plan", _l("Attestatsiyadan oldingi zaxira"), _l("Yakuniy diagnostika va takrorlash uchun"), _l("kun")),
    "tutor_daily": Item(20, 0, 200, "ai", _l("AI tutor: kunlik savollar"), _l("Bitta foydalanuvchiga; AI ulangach ishlaydi (0 — o‘chirilgan)"), _l("ta")),
}


def _stored() -> dict:
    if not has_app_context():
        return {}
    if "settings" not in g:
        g.settings = dict(db.session.execute(select(Setting.key, Setting.value).where(Setting.key.in_(ITEMS))).all())
    return g.settings


def get(key: str) -> int:
    item = ITEMS[key]
    v = _stored().get(key, item.default)
    return v if isinstance(v, int) and not isinstance(v, bool) and item.low <= v <= item.high else item.default


def save(values: dict[str, int], actor_id: int) -> dict[str, list[int]]:
    """Commit qilmaydi. Natija — o'zgarganlari: {kalit: [eski, yangi]}."""
    changed = {}
    for key, new in values.items():
        old = get(key)
        if new == old:
            continue
        changed[key] = [old, new]
        row = db.session.get(Setting, key)
        if new == ITEMS[key].default:
            if row is not None:
                db.session.delete(row)
        elif row is None:
            db.session.add(Setting(key=key, value=new, updated_by=actor_id))
        else:
            row.value, row.updated_by = new, actor_id
    db.session.flush()
    g.pop("settings", None)
    return changed
