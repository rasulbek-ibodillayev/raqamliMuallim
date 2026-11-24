"""Bir martalik havolalar: ekspert taklifnomasi (72 soat) va parolni tiklash havolasi (24 soat).

Havola tokeni bazada saqlanmaydi: SECRET_KEY bilan imzolangan (HMAC). Shuning uchun admin havolani istalgan payt qayta
nusxalay oladi, baza nusxasi esa havolani bermaydi. Tokenda ism yoki telefon yo'q (URL, server loglari va Referer'da ko'rinmasin).
- Taklifnoma: qayta yuborilsa nonce oshadi — eski havola ishlamaydi; bekor qilinsa qator o'chadi; ishlatilgani used_at.
- Parol havolasi: imzoga parol xeshi kiradi — parol almashishi bilan havola o'z-o'zidan bekor bo'ladi.

Yetkazish: Telegram bot va email ulangach (11, 12-bosqichlar) avtomatik; hozir admin havolani nusxalab o'zi yuboradi.
"""
import base64
import hashlib
import hmac
import time
from datetime import datetime, timedelta, timezone

from flask import current_app
from sqlalchemy import delete, select

from .extensions import db
from .models import ExpertInvite, User

MAX_AGE = 72 * 3600
RESET_AGE = 24 * 3600


def _sig(*parts) -> str:
    raw = hmac.new(current_app.config["SECRET_KEY"].encode(), "|".join(map(str, parts)).encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(raw[:21]).decode()


def _same(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


# ---------------- Ekspert taklifnomasi ----------------

def make(name: str, contact: str, areas: list[int], perms: list[str], actor_id: int | None = None) -> ExpertInvite:
    """Shu manzilga avvalgi taklifnoma bo'lsa — yangilanadi (eski havola bekor bo'ladi). Commit qilmaydi."""
    db.session.execute(delete(ExpertInvite).where(ExpertInvite.used_at < datetime.now(timezone.utc) - timedelta(days=30)))
    inv = db.session.scalar(select(ExpertInvite).where(ExpertInvite.contact == contact))
    if inv is None:
        inv = ExpertInvite(contact=contact, nonce=0)
        db.session.add(inv)
    else:
        inv.nonce += 1
    inv.name, inv.areas, inv.perms, inv.created_by = name, list(areas), list(perms), actor_id
    inv.sent_at, inv.used_at = datetime.now(timezone.utc), None
    db.session.flush()
    return inv


def resend(inv: ExpertInvite) -> None:
    inv.nonce, inv.sent_at = inv.nonce + 1, datetime.now(timezone.utc)
    db.session.flush()


def token(inv: ExpertInvite) -> str:
    return f"{inv.id}-{_sig('invite', inv.id, inv.nonce)}"


def expired(inv: ExpertInvite) -> bool:
    return (datetime.now(timezone.utc) - inv.sent_at).total_seconds() > MAX_AGE


def read(value: str) -> tuple[str, ExpertInvite | None]:
    """→ (holat, taklifnoma). holat: "valid" | "expired" | "invalid" | "used"."""
    head, _sep, _tail = value.partition("-")
    inv = db.session.get(ExpertInvite, int(head)) if head.isdigit() and len(head) < 19 else None
    if inv is None or not _same(value, token(inv)):
        return "invalid", None
    if inv.used_at is not None:
        return "used", inv
    return ("expired", None) if expired(inv) else ("valid", inv)


def pending() -> list[ExpertInvite]:
    return list(db.session.scalars(select(ExpertInvite).where(ExpertInvite.used_at.is_(None)).order_by(ExpertInvite.sent_at.desc())))


def channel(contact: str) -> str:
    return "email" if "@" in contact else "telegram"


# ---------------- Parolni tiklash havolasi ----------------

def _reset_sig(user: User, exp: int) -> str:
    return _sig("reset", user.id, exp, user.password_hash or "")


def reset_token(user: User) -> str:
    exp = int(time.time()) + RESET_AGE
    return f"{user.id}-{exp}-{_reset_sig(user, exp)}"


def read_reset(value: str) -> User | None:
    uid, _sep, rest = value.partition("-")
    exp, _sep, sig = rest.partition("-")
    if not (uid.isdigit() and exp.isdigit() and len(uid) < 19 and len(exp) < 12) or int(exp) < time.time():
        return None
    user = db.session.get(User, int(uid))
    return user if user is not None and user.is_active and _same(sig, _reset_sig(user, int(exp))) else None
