"""Fon vazifalari ro'yxati. Yangi vazifa: @task(...) bilan funksiya; navbatga qo'yish — jobs.add("tur", {...}).

Vaqtlar Toshkent bo'yicha, yuklama eng kam paytda. Keyingi bosqichlar shu yerga qo'shiladi: kod va xabar yuborish (11, 12),
audio (14), AI savol (13b), faol bo'lmagan akkauntlar (10b).
"""
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import current_app
from flask_babel import lazy_gettext as _l
from sqlalchemy import text

from ..extensions import db
from . import archive, exam_clock, notify, offline, stock
from .jobs import SLOW, Daily, task

FILE_DAYS, INVITE_DAYS, DEAD_DAYS = 7, 30, 30
_REF = r"uploads/q/[0-9a-f]{24}\.(?:png|jpg|webp)"


@task("archive", _l("Eski testlarni siqish"), lane=SLOW, lease=3600, every=Daily(2, 30))
def archive_old(_data: dict) -> dict:
    return {"n": archive.compress_old()}


@task("cleanup", _l("Muddati o‘tgan yozuvlarni tozalash"), lane=SLOW, every=Daily(3, 0))
def cleanup(_data: dict) -> dict:
    """Urinishlar hisobi, 30 kunlik bildirishnomalar, ishlatilgan taklifnomalar, AI keshi, eski to'xtagan vazifalar."""
    now = datetime.now(timezone.utc)
    n = offline.purge()
    n += exam_clock.close_all()                      # vazifasi yo'qolib qolgan testlar (masalan, eski versiyadan)
    for sql, before in (("DELETE FROM rate_limits WHERE until < :t", now),
                        ("DELETE FROM notifications WHERE created_at < :t", now - timedelta(days=notify.KEEP_DAYS)),
                        ("DELETE FROM expert_invites WHERE used_at < :t", now - timedelta(days=INVITE_DAYS)),
                        ("DELETE FROM ai_cache WHERE expires_at < :t", now),
                        # To'xtagan vazifada vaqt yo'q: 30 kun ko'rinib turishi uchun done_at to'xtagan vaqt bo'ladi
                        ("UPDATE jobs SET done_at = :t WHERE run_at IS NULL AND done_at IS NULL", now)):
        n += db.session.execute(text(sql), {"t": before}).rowcount
    n += db.session.execute(text("DELETE FROM jobs WHERE run_at IS NULL AND done_at < :t"),
                            {"t": now - timedelta(days=DEAD_DAYS)}).rowcount
    return {"n": n}


@task("files", _l("Keraksiz rasmlarni o‘chirish"), lane=SLOW, every=Daily(3, 30, weekday=6))
def orphan_files(_data: dict) -> dict:
    """Hech bir savol, uning eski versiyasi va dars bloki ishlatmaydigan, 7 kundan eski rasmlar (masalan, saqlanmay qolgan)."""
    folder = Path(current_app.static_folder) / "uploads" / "q"
    # Ishlab chiqishda bir nechta baza (nusxa, zaxira) bitta papkani ishlatadi: boshqasining rasmi o'chib ketmasin
    if current_app.debug or not folder.is_dir():
        return {"n": 0, "kb": 0}
    old = time.time() - FILE_DAYS * 86400
    files = [f for f in folder.iterdir() if re.fullmatch(_REF, f"uploads/q/{f.name}") and f.stat().st_mtime < old]
    used = set()
    for table, col in (("questions", "data"), ("question_versions", "snapshot"), ("content_blocks", "data")):
        used |= {v for (v,) in db.session.execute(text(
            f"SELECT DISTINCT m[1] FROM {table}, regexp_matches({col}::text, :re, 'g') AS m WHERE {col}::text LIKE '%uploads/q/%'"),
            {"re": _REF})}
    n = size = 0
    for f in files:
        if f"uploads/q/{f.name}" not in used:
            size += f.stat().st_size
            os.remove(f)
            n += 1
    return {"n": n, "kb": round(size / 1024)}


@task("exam_end", _l("Attestatsiya testini yakunlash"))
def exam_end(data: dict) -> dict:
    """Vaqt tugadi. Test to'xtatib turilgan bo'lsa hech narsa qilmaydi: davom ettirilganda vazifa qaytadan qo'yiladi."""
    return {"n": int(exam_clock.close_by_id(data["id"]))}


@task("stock", _l("Savoli tugayotgan darslarni topish"), lane=SLOW, lease=1800, every=Daily(4, 0))
def question_stock(_data: dict) -> dict:
    return stock.compute()
