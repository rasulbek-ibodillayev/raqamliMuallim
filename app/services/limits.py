"""Urinishlarni cheklash: kirish, kod yuborish va tekshirish, maxfiy so'z, joriy parol (rate_limits jadvali, Redis'siz).

- Hisob bazada: cookie'ni o'chirish yoki eski cookie'ni qayta yuborish urinishlar sonini tiklamaydi, hamma worker bir xil ko'radi.
- Urinish tekshiruvdan OLDIN sanaladi (bitta atomar so'rov): parallel yuborilgan 100 ta taxmin chegaradan o'tib ketmaydi.
  Muvaffaqiyatda refund() yoki clear() qaytaradi — to'g'ri kirganlar hisobga yozilmaydi.
- Alohida tranzaksiyada yoziladi: sahifa kodi rollback qilsa ham urinish hisobda qoladi.
- Kalit — 8 baytli HMAC: jadvalda telefon, email yoki IP yo'q. UNLOGGED: WAL yozilmaydi, baza qulab tushsa hisob noldan boshlanadi.
- IP chegarasi keng: maktab yoki mobil operator orqasida yuzlab odam bitta IP bilan chiqadi. Asosiy himoya — login bo'yicha.
"""
import hashlib
import ipaddress
import random
from dataclasses import dataclass

from flask import current_app, g, request
from flask_babel import gettext as _
from sqlalchemy import text

from ..extensions import db

MINUTE, HOUR, DAY = 60, 3600, 86400

# nom: (urinishlar, davr soniyada)
RULES: dict[str, tuple[int, int]] = {
    "login_ip": (100, 15 * MINUTE),       # bitta IP'dan noto'g'ri kirishlar
    "login": (5, 15 * MINUTE),            # bitta akkauntga bitta IP'dan
    "login_all": (30, HOUR),              # bitta akkauntga hamma IP'lardan (begona odam bitta IP bilan egasini bloklay olmaydi: 4 × 5 < 30)
    "code_ip": (200, HOUR),               # kod so'rash (raqam ro'yxatdan o'tganini terib chiqishdan ham himoya)
    "code": (5, 15 * MINUTE),             # bitta raqam yoki emailga
    "code_day": (15, DAY),
    "otp": (5, 15 * MINUTE),              # bitta kodni tekshirish
    "secret_ip": (50, 30 * MINUTE),
    "secret": (5, 30 * MINUTE),           # maxfiy so'z: bitta akkauntga, IP'dan qat'i nazar (so'z paroldan kuchsizroq)
    "secret_day": (15, DAY),
    "pw": (5, 15 * MINUTE),               # profilda joriy parol (kirgan foydalanuvchi)
}


@dataclass(frozen=True)
class Result:
    wait: int          # 0 — ruxsat; aks holda necha soniyadan keyin
    left: int          # shu urinishdan keyin nechta qoladi (eng kami)

    @property
    def blocked(self) -> bool:
        return self.wait > 0


# Chegaraga yetgan qator yozilmaydi (WHERE): hujum paytida o'lik qatorlar ko'paymaydi va muddat cho'zilmaydi
_TAKE = text("""
    INSERT INTO rate_limits AS r (key, n, until) VALUES (:key, 1, now() + make_interval(secs => :secs))
    ON CONFLICT (key) DO UPDATE SET n = CASE WHEN r.until <= now() THEN 1 ELSE r.n + 1 END,
                                    until = CASE WHEN r.until <= now() THEN excluded.until ELSE r.until END
    WHERE r.until <= now() OR r.n < :n
    RETURNING r.n""")
_WAIT = text("SELECT GREATEST(1, CEIL(EXTRACT(EPOCH FROM until - now())))::int FROM rate_limits WHERE key = :key")
_REFUND = text("UPDATE rate_limits SET n = n - 1 WHERE key = :key AND n > 0 AND until > now()")
_CLEAR = text("DELETE FROM rate_limits WHERE key = :key")
_PURGE = text("DELETE FROM rate_limits WHERE key IN (SELECT key FROM rate_limits WHERE until < now() LIMIT 1000)")


def _key(rule: str, subject) -> int:
    secret = hashlib.sha256(current_app.config["SECRET_KEY"].encode()).digest()
    raw = hashlib.blake2b(f"{rule}\0{subject}".encode(), key=secret, digest_size=8).digest()
    return int.from_bytes(raw, "big", signed=True)


def client_ip() -> str:
    """Mijoz IP'si. IPv6'da /64 — bitta uyga butun tarmoq beriladi, manzilni almashtirib chegaradan qochib bo'lmasin.
    Proksi ortida RM_PROXY_HOPS berilishi shart (app/__init__.py), aks holda hamma bitta IP bo'lib ko'rinadi."""
    raw = request.remote_addr or ""
    try:
        ip = ipaddress.ip_address(raw)
    except ValueError:
        return raw
    if ip.version == 6:
        return str(ip.ipv4_mapped) if ip.ipv4_mapped else str(ipaddress.ip_network((ip, 64), strict=False))
    return raw


def take(*pairs: tuple[str, object]) -> Result:
    """(qoida, kim) juftliklarini tartib bilan sanaydi va birinchi to'lganida to'xtaydi — keyingilarining hisobi sarflanmaydi.
    Shuning uchun tartib: avval torroq doira (IP, akkaunt + IP), keyin umumiysi."""
    left = min(RULES[rule][0] for rule, _subject in pairs)
    with db.engine.begin() as conn:
        for rule, subject in pairs:
            limit, secs = RULES[rule]
            key = _key(rule, subject)
            n = conn.scalar(_TAKE, {"key": key, "n": limit, "secs": secs})
            if n is None:
                wait = conn.scalar(_WAIT, {"key": key}) or 1
                g.retry_after = wait                       # forms.respond → 429 va Retry-After
                current_app.logger.warning("Cheklov: %s", rule)
                return Result(wait, 0)
            left = min(left, limit - n)
        if random.random() < 0.01:
            conn.execute(_PURGE)
    return Result(0, left)


def refund(*pairs: tuple[str, object]) -> None:
    """Muvaffaqiyatli urinish hisobdan qaytariladi."""
    with db.engine.begin() as conn:
        for rule, subject in pairs:
            conn.execute(_REFUND, {"key": _key(rule, subject)})


def clear(*pairs: tuple[str, object]) -> None:
    with db.engine.begin() as conn:
        for rule, subject in pairs:
            conn.execute(_CLEAR, {"key": _key(rule, subject)})


def clear_all() -> int:
    with db.engine.begin() as conn:
        return conn.execute(text("DELETE FROM rate_limits")).rowcount


def wait_text(seconds: int) -> str:
    """«12 daqiqadan» / «3 soatdan» — «… keyin qayta urinib ko'ring» oldidan."""
    return (_("%(n)s daqiqadan", n=-(-seconds // MINUTE)) if seconds <= HOUR else _("%(n)s soatdan", n=-(-seconds // HOUR)))


def message(wait: int) -> str:
    return _("Juda ko‘p urinish. %(t)s keyin qayta urinib ko‘ring", t=wait_text(wait))
