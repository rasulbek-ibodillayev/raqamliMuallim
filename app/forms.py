"""Formalarni serverda tekshirish va javob qaytarish.

Har bir forma ikki xil ishlaydi:
- JS bilan (rmForm, fetch + Accept: application/json): {"ok", "message", "errors", "redirect"} qaytadi,
  xatolar maydon yonida ko'rsatiladi, sahifa qayta yuklanmaydi;
- JS'siz (oddiy POST): muvaffaqiyatda flash xabar + redirect (PRG), xatoda shablon xatolar bilan qayta chiziladi (422).

Backend ulanganda bu yerdagi tekshiruvlar qoladi, faqat "saqlash" qismi servis qatlamiga o'tadi.
"""
import re
from datetime import date

from flask import flash, jsonify, redirect, render_template, request
from flask_babel import gettext as _

PHONE_RE = re.compile(r"^\+?998\d{9}$")
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[A-Za-z]{2,}$")
NAME_RE = re.compile(r"^[A-Za-zА-Яа-яЁёЎўҚқҒғҲҳ‘’ʻʼ'`\- ]{2,80}$")

REGIONS = ["Toshkent shahri", "Toshkent viloyati", "Andijon viloyati", "Buxoro viloyati", "Farg‘ona viloyati",
           "Jizzax viloyati", "Xorazm viloyati", "Namangan viloyati", "Navoiy viloyati", "Qashqadaryo viloyati",
           "Samarqand viloyati", "Sirdaryo viloyati", "Surxondaryo viloyati", "Qoraqalpog‘iston Respublikasi"]

OBJECTION_REASONS = ["wrong_key", "also_correct", "unclear", "media", "other"]


def wants_json() -> bool:
    return request.accept_mimetypes.best == "application/json"


def norm_phone(value: str) -> str:
    """'90 123-45-67', '+998 90 123 45 67' → '+998901234567'."""
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 9:
        digits = "998" + digits
    return "+" + digits if digits else ""


def fmt_phone(p: str) -> str:
    """'+998931112233' → '+998 93 111 22 33'."""
    d = (p or "").lstrip("+")
    return f"+{d[:3]} {d[3:5]} {d[5:8]} {d[8:10]} {d[10:]}" if len(d) == 12 else p


def field(name: str, default: str = "") -> str:
    return (request.form.get(name) or default).strip()


def otp_code(name: str = "otp") -> str:
    """6 ta alohida katakdan (bir xil name) yoki bitta maydondan kod."""
    parts = request.form.getlist(name)
    return "".join(p.strip() for p in parts)


# ---------- tekshiruvchilar: xato matnini yoki None qaytaradi ----------

def required(v, msg=None):
    return None if v else (msg or _("Maydonni to‘ldiring"))


def check_phone(v):
    return None if PHONE_RE.match(norm_phone(v)) else _("Telefon raqam noto‘g‘ri: +998 va 9 ta raqam bo‘lishi kerak")


def check_email(v):
    return None if EMAIL_RE.match(v or "") else _("Email manzil noto‘g‘ri")


def check_login(v):
    if not v:
        return _("Telefon raqam yoki emailni kiriting")
    return check_email(v) if "@" in v else check_phone(v)


def check_password(v):
    if len(v or "") < 8:
        return _("Parol kamida 8 ta belgidan iborat bo‘lsin")
    if not (re.search(r"\d", v) and re.search(r"[^\W\d_]", v)):
        return _("Parolda harf ham, raqam ham bo‘lsin")
    return None


def check_otp(v):
    return None if re.fullmatch(r"\d{6}", v or "") else _("6 xonali kodni to‘liq kiriting")


def check_name(v, what="first"):
    """what: "first" (ism) yoki "last" (familiya) — xabarlar to'liq jumla bo'lib tarjima qilinadi."""
    if not v:
        return _("Ismni kiriting") if what == "first" else _("Familiyani kiriting")
    if NAME_RE.match(v):
        return None
    return _("Ism faqat harflardan iborat bo‘lsin") if what == "first" else _("Familiya faqat harflardan iborat bo‘lsin")


def norm_secret(v: str) -> str:
    """Maxfiy so'z: bo'sh joylar qisqartiriladi, katta-kichik harf va o'zbekcha tutuq belgisi farqlanmaydi.
    Backendda faqat shu ko'rinishning xeshi saqlanadi (parol kabi)."""
    return re.sub(r"\s+", " ", (v or "").strip().lower()).replace("’", "‘").replace("'", "‘").replace("ʻ", "‘")


def check_secret(v, password=""):
    s = norm_secret(v)
    if not s:
        return _("Maxfiy so‘zni kiriting")
    if len(s) < 4:
        return _("Maxfiy so‘z kamida 4 ta belgidan iborat bo‘lsin")
    if len(s) > 64:
        return _("Maxfiy so‘z 64 belgidan oshmasin")
    if password and s == norm_secret(password):
        return _("Maxfiy so‘z paroldan farq qilsin")
    return None


def check_date(v):
    try:
        d = date.fromisoformat(v)
    except (TypeError, ValueError):
        return _("Sanani tanlang")
    return None if d >= date.today() else _("Sana o‘tib ketgan bo‘lmasin")


def validate(rules: dict) -> dict:
    """{"maydon": (qiymat, tekshiruvchi, ...)} → {"maydon": "xato matni"} (birinchi xato)."""
    errors = {}
    for name, (value, *checks) in rules.items():
        for check in checks:
            msg = check(value)
            if msg:
                errors[name] = msg
                break
    return errors


# ---------- javob ----------

def respond(*, errors=None, message=None, redirect_to=None, template=None, data=None, **ctx):
    """Forma natijasi. errors bo'lsa — 422; aks holda muvaffaqiyat."""
    if errors:
        if wants_json():
            return jsonify(ok=False, errors=errors, message=_("Xatolarni tuzating")), 422
        return render_template(template, errors=errors, form=request.form, **ctx), 422
    if wants_json():
        return jsonify(ok=True, message=message, redirect=redirect_to, data=data or {})
    if message:
        flash(message, "success")
    return redirect(redirect_to or request.referrer or "/")
