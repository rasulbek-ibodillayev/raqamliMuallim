"""Yuklangan rasmlarni saqlash (savol rasmi, chizma).

- Faqat PNG, JPEG, WebP; turi fayl nomidan emas, birinchi baytlaridan aniqlanadi.
  SVG qabul qilinmaydi: ichida skript bo'lishi mumkin (sxemalar Mermaid matni sifatida saqlanadi).
- Hajmi ≤ 2 MB (so'rovning umumiy chegarasi — MAX_CONTENT_LENGTH).
- Fayl nomi — mazmun xeshi: bir xil rasm ikki marta saqlanmaydi, nomdan foydalanuvchi kiritgan matn o'tmaydi.
- Joyi: app/static/uploads/q/ ; bazaga static'ga nisbatan yo'l yoziladi (masalan "uploads/q/ab12….webp").
"""
import hashlib
import os
from pathlib import Path

from flask import current_app

MAX_BYTES = 2 * 1024 * 1024
SIGNATURES = [(b"\x89PNG\r\n\x1a\n", "png"), (b"\xff\xd8\xff", "jpg")]


class UploadError(ValueError):
    pass


def _kind(head: bytes) -> str | None:
    for sig, ext in SIGNATURES:
        if head.startswith(sig):
            return ext
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    return None


def save_image(file) -> str | None:
    """werkzeug FileStorage → static'ga nisbatan yo'l. Fayl tanlanmagan bo'lsa None; noto'g'ri bo'lsa UploadError."""
    if file is None or not file.filename:
        return None
    data = file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise UploadError("Rasm 2 MB dan oshmasin")
    ext = _kind(data[:16])
    if ext is None:
        raise UploadError("Faqat PNG, JPEG yoki WebP rasm yuklang")
    name = f"{hashlib.sha256(data).hexdigest()[:24]}.{ext}"
    folder = Path(current_app.static_folder) / "uploads" / "q"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    if path.exists():
        os.utime(path)                # qayta yuklandi: tozalash (tasks.orphan_files) hozir o'chirib yubormasin
    else:
        path.write_bytes(data)
    return f"uploads/q/{name}"
