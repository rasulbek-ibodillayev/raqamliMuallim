"""Ekspert taklifnomasi: admin yaratadi, ekspert havola orqali parol o'rnatib akkauntini faollashtiradi.

Havoladagi token — tasodifiy, ichida hech qanday ma'lumot yo'q (ism yoki telefon URL'da, server loglarida va
Referer'da ko'rinmasin). Taklifnoma ma'lumoti (ism, telefon/email, yo'nalishlar, huquqlar) serverda saqlanadi
va 72 soat amal qiladi. Ishlatilgan yoki bekor qilingan (qayta yuborilganda eskisi ham) token ishlamaydi.
Namunada — server xotirasida (qayta ishga tushganda tozalanadi). Backendda: expert_invites jadvali
(token_hash, created_at, used_at, revoked_at) — tokenning o'zi emas, faqat xeshi saqlanadi.

Yetkazish:
- email — xat bilan;
- telefon — Telegram bot orqali. Diqqat: Telegram bot faqat o'zini /start qilgan foydalanuvchiga yoza oladi.
  Ekspert botga hali yozmagan bo'lsa, admin havolani nusxalab o'zi yuboradi (sahifada «Havolani nusxalash»).
"""
import secrets
import time

MAX_AGE = 72 * 3600
_STORE = {}   # namuna: token → {"n", "c", "a", "p", "at", "used", "revoked"}


def make(name: str, contact: str, areas: list, perms: list) -> str:
    token = secrets.token_urlsafe(24)
    _STORE[token] = {"n": name, "c": contact, "a": list(areas), "p": list(perms), "at": time.time(),
                     "used": False, "revoked": False}
    return token


def read(token: str):
    """→ (holat, ma'lumot). holat: "valid" | "expired" | "invalid" | "used"."""
    inv = _STORE.get(token)
    if not inv or inv["revoked"]:
        return "invalid", None
    if inv["used"]:
        return "used", inv
    if time.time() - inv["at"] > MAX_AGE:
        return "expired", None
    return "valid", inv


def mark_used(token: str):
    if token in _STORE:
        _STORE[token]["used"] = True


def revoke(token: str):
    if token in _STORE:
        _STORE[token]["revoked"] = True


def channel(contact: str) -> str:
    return "email" if "@" in contact else "telegram"
