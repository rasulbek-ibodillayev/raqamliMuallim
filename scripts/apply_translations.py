"""app/translations/ru_core.py lug'atini ru/messages.po ga yozadi va .mo ni kompilyatsiya qiladi.

    .venv/Scripts/python scripts/apply_translations.py

Mavjud (qo'lda kiritilgan) tarjimalar ustidan yozilmaydi — faqat bo'sh msgstr to'ldiriladi.
"""
import sys
from pathlib import Path

from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po, write_po

ROOT = Path(__file__).resolve().parent.parent / "app" / "translations"
sys.path.insert(0, str(ROOT))
from ru_core import RU  # noqa: E402

po_path = ROOT / "ru" / "LC_MESSAGES" / "messages.po"
with po_path.open("rb") as f:
    cat = read_po(f, locale="ru")

filled = 0
for msg in cat:
    if msg.id and not msg.string and msg.id in RU:
        msg.string = RU[msg.id]
        filled += 1
total = sum(1 for m in cat if m.id)
done = sum(1 for m in cat if m.id and m.string)
with po_path.open("wb") as f:
    write_po(f, cat, width=0)
with (po_path.with_suffix(".mo")).open("wb") as f:
    write_mo(f, cat)
missing = sorted(set(RU) - {m.id for m in cat if m.id})
print(f"To'ldirildi: {filled}. Tarjima qilingan: {done} / {total} ({done * 100 // total}%)")
if missing:
    print("Katalogda yo'q (eskirgan) kalitlar:", len(missing))
