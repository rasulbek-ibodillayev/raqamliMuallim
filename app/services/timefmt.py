"""Sana va vaqtni ko'rsatish (Toshkent vaqti, UTC+5; yozgi vaqt yo'q)."""
from datetime import datetime, timedelta, timezone

from flask_babel import gettext as _
from flask_babel import lazy_gettext as _l

TASHKENT = timezone(timedelta(hours=5))
MONTHS = [_l("yanvar"), _l("fevral"), _l("mart"), _l("aprel"), _l("may"), _l("iyun"), _l("iyul"), _l("avgust"),
          _l("sentabr"), _l("oktabr"), _l("noyabr"), _l("dekabr")]


def now() -> datetime:
    return datetime.now(TASHKENT)


def day_month(d) -> str:
    return f"{d.day}-{MONTHS[d.month - 1]}"


def when(dt: datetime | None) -> str:
    """Bugun, 14:20 · Kecha, 18:45 · 12-noyabr · 12-noyabr 2025."""
    if dt is None:
        return ""
    dt, today = dt.astimezone(TASHKENT), now().date()
    days = (today - dt.date()).days
    if days == 0:
        return f"{_('Bugun')}, {dt:%H:%M}"
    if days == 1:
        return f"{_('Kecha')}, {dt:%H:%M}"
    return day_month(dt) if dt.year == today.year else f"{day_month(dt)} {dt.year}"
