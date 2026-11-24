"""Bildirishnomalar: ixcham qator (turi, havola id'si, eski va yangi foiz) — matn ko'rsatishda tuziladi.

- 30 kundan eskisi ko'rsatilmaydi va shu foydalanuvchiga keyingisi yozilganda o'chadi (alohida fon vazifasi kerak emas).
- O'qilganlik har qatorda emas, users.notif_seen_at da: undan keyingilari — yangi.
- Yakunlanmagan test eslatmasi saqlanmaydi: har safar bazadan hisoblanadi.
"""
from datetime import datetime, timedelta, timezone

from flask import url_for
from flask_babel import gettext as _
from sqlalchemy import delete, select

from ..extensions import db
from ..models import Notification, TestAttempt, User
from . import attempts as at
from .timefmt import when

KEEP_DAYS = 30
LIMIT = 20
OBJ_ACCEPTED, OBJ_REJECTED, RECALC, DROPPED = 1, 2, 3, 4


def _old():
    return datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)


def add(user_id: int, kind: int, ref_id: int | None = None, old_pct: float | None = None, new_pct: float | None = None) -> None:
    """Commit qilmaydi."""
    db.session.execute(delete(Notification).where(Notification.user_id == user_id, Notification.created_at < _old())
                       .execution_options(synchronize_session=False))
    db.session.add(Notification(user_id=user_id, kind=kind, ref_id=ref_id,
                                old_pct=None if old_pct is None else round(old_pct),
                                new_pct=None if new_pct is None else round(new_pct)))


def _view(n: Notification, names: dict[int, str]) -> dict:
    pct = (_("Natijangiz %(a)s%% → %(b)s%% ga qayta hisoblandi", a=n.old_pct, b=n.new_pct)
           if n.old_pct is not None and n.new_pct is not None and n.old_pct != n.new_pct else None)
    if n.kind in (OBJ_ACCEPTED, OBJ_REJECTED):
        ok = n.kind == OBJ_ACCEPTED
        return {"icon": "shield", "title": _("E’tirozingiz qabul qilindi") if ok else _("E’tirozingizga javob keldi"),
                "text": pct or _("Ekspert xulosasini o‘qing"), "url": url_for("user.objections")}
    name = names.get(n.ref_id)
    url = url_for("user.result_detail", rid=n.ref_id) if name else url_for("user.results")
    title = _("Natijangiz qayta hisoblandi") if n.kind == RECALC else _("Savol hisobdan chiqarildi")
    text = pct or (_("Savol ekspertizadan o‘tmadi, natijangiz o‘zgarmadi") if n.kind == DROPPED else _("Natijangiz o‘zgarmadi"))
    return {"icon": "refresh" if n.kind == RECALC else "info", "title": title, "text": f"{name}: {text}" if name else text, "url": url}


def list_for(user: User) -> list[dict]:
    """Qo'ng'iroqcha ro'yxati: avval yakunlanmagan testlar, keyin bildirishnomalar (yangisi birinchi)."""
    from ..views.test import attempt_url, type_names
    open_ = list(db.session.scalars(select(TestAttempt).where(TestAttempt.user_id == user.id, TestAttempt.status == "in_progress")
                                    .order_by(TestAttempt.started_at.desc()).limit(3)))
    rows = list(db.session.scalars(select(Notification).where(Notification.user_id == user.id, Notification.created_at >= _old())
                                   .order_by(Notification.id.desc()).limit(LIMIT)))
    refs = {n.ref_id for n in rows if n.kind in (RECALC, DROPPED) and n.ref_id}
    mine = list(db.session.scalars(select(TestAttempt).where(TestAttempt.id.in_(refs), TestAttempt.user_id == user.id))) if refs else []
    names = at.names([*open_, *mine], type_names()) if open_ or mine else {}
    seen = user.notif_seen_at
    out = [{"icon": "clipboard", "title": _("Tugatilmagan testingiz bor"), "text": names[a.id], "when": when(a.started_at),
            "url": attempt_url(a), "unread": False} for a in open_]
    return out + [{**_view(n, names), "when": when(n.created_at), "unread": seen is None or n.created_at > seen} for n in rows]


def mark_seen(user: User) -> None:
    user.notif_seen_at = datetime.now(timezone.utc)
    db.session.commit()
