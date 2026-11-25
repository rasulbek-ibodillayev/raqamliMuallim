"""Tasdiqlash kodlari: so'rash va tekshirish (ro'yxatdan o'tish, parolni tiklash, telefon/emailni almashtirish).

Kodni yetkazish hali ulanmagan (11 — Telegram bot, 12 — email). Shu paytgacha kod faqat ishlab chiqishda 123456;
serverda hech qanday kod to'g'ri kelmaydi — aks holda istalgan akkauntni shu kod bilan egallab olish mumkin bo'lardi.
"""
import secrets

from flask import current_app
from flask_babel import gettext as _

from . import limits

DEMO = "123456"


def target(contact: str) -> str:
    """Chegara kimga yozilishi: «90 123-45-67» va «+998901234567» — bitta raqam."""
    from ..forms import norm_phone
    return contact.strip().lower() if "@" in contact else norm_phone(contact)


def _dev() -> bool:
    return bool(current_app.debug or current_app.config.get("DEV_TOOLS"))


def lookup() -> str | None:
    """Kod so'rashning birinchi qadami: IP chegarasi. «Bunday raqam bor/yo'q» javobidan oldin chaqiriladi."""
    r = limits.take(("code_ip", limits.client_ip()))
    return limits.message(r.wait) if r.blocked else None


def send(contact: str) -> str | None:
    """Kod yuborishga ruxsat; xato matni yoki None. Yangi kod eskisining noto'g'ri urinishlarini tozalaydi."""
    if not _dev():
        return _("Kod yuborish hali ulanmagan. Yordam xizmatiga yozing")
    who = target(contact)
    r = limits.take(("code", who), ("code_day", who))
    if r.blocked:
        return limits.message(r.wait)
    limits.clear(("otp", who))
    return None


def verify(contact: str, code: str) -> tuple[str | None, bool]:
    """→ (xato matni yoki None, kod bekor bo'ldimi). 5 ta xatodan keyin to'g'ri kod ham qabul qilinmaydi."""
    who = target(contact)
    r = limits.take(("otp", who))
    if r.blocked:
        return _("Kod 5 marta noto‘g‘ri kiritildi. Yangi kod so‘rang"), True
    if _dev() and secrets.compare_digest(code.encode(), DEMO.encode()):
        limits.clear(("otp", who))
        return None, False
    if not r.left:
        return _("Kod 5 marta noto‘g‘ri kiritildi. Yangi kod so‘rang"), True
    return _("Kod noto‘g‘ri. Yana %(n)s ta urinish qoldi", n=r.left), False
