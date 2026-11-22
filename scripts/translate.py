"""Saytni tanlangan tillarga o'tkazuvchi dastur (ru, en, kaa — qoraqalpoq).

    .venv/Scripts/python scripts/translate.py            # lug'atlardan to'ldirish + kompilyatsiya
    .venv/Scripts/python scripts/translate.py --extract  # avval shablonlardan yangi matnlarni yig'ish
    .venv/Scripts/python scripts/translate.py --lang en  # faqat bitta til

Ish tartibi har bir til uchun:
1) (--extract) pybabel extract/update — shablon va Python'dagi barcha _("…") matnlari katalogga tushadi;
2) qo'lda tekshirilgan lug'at (app/translations/core_<til>.py, rus tili uchun ru_core.py) bo'sh satrlarni to'ldiradi;
3) RM_TRANSLATE_URL berilgan bo'lsa (o'z serverimizdagi LibreTranslate: docker compose up -d translate →
   http://localhost:5050/translate), qolgan satrlar mashina tarjimasi bilan to'ldiriladi.
   Avval xizmat qo'llaydigan tillar so'raladi (/languages). Argos modellarida o'zbek va qoraqalpoq tili yo'q,
   shuning uchun manba sifatida tayyor ruscha tarjima ishlatiladi (uz → [ru tarjimasi] → en). Xizmat qo'llamaydigan
   til (kaa) mashina tarjimasisiz qoladi — faqat lug'at va tarjimon. %(n)s, %%, {n} kabi o'rinbosarlar
   himoyalanadi; natija keshlanadi (app/translations/<til>/mt_cache.json) va «#. mashina tarjimasi» izohi bilan
   belgilanadi — keyin tarjimon tekshiradi;
4) .mo fayllari kompilyatsiya qilinadi va qamrov (foiz) chiqariladi.

Mavjud (qo'lda kiritilgan) tarjimalar ustidan hech qachon yozilmaydi.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po, write_po

BASE = Path(__file__).resolve().parent.parent
ROOT = BASE / "app" / "translations"
sys.path.insert(0, str(ROOT))

LANGS = ("ru", "en", "kaa")
MT_NOTE = "mashina tarjimasi"
PLACEHOLDER = re.compile(r"%\([a-z_]+\)s|%%|\{[a-z_]+\}|<[^>]+>")


def core(lang):
    if lang == "ru":
        from ru_core import RU
        return RU
    if lang == "en":
        from core_en import EN
        return EN
    from core_kaa import KAA
    return KAA


def extract():
    pybabel = [sys.executable, "-m", "babel.messages.frontend"]
    subprocess.run(pybabel + ["extract", "-F", "babel.cfg", "-k", "_l", "-o", str(ROOT / "messages.pot"), "--no-wrap", "."],
                   cwd=BASE, check=True)
    for lang in LANGS:
        cmd = "update" if (ROOT / lang / "LC_MESSAGES" / "messages.po").exists() else "init"
        subprocess.run(pybabel + [cmd, "-i", str(ROOT / "messages.pot"), "-d", str(ROOT), "-l", lang, "--no-wrap"],
                       cwd=BASE, check=True)


_SUPPORTED = None


def supported():
    """Tarjima xizmati qo'llaydigan tillar: {manba: {nishonlar}}. Xizmat yo'q bo'lsa — bo'sh."""
    global _SUPPORTED
    if _SUPPORTED is None:
        _SUPPORTED = {}
        url = os.environ.get("RM_TRANSLATE_URL")
        if url:
            try:
                with urllib.request.urlopen(url.rsplit("/", 1)[0] + "/languages", timeout=10) as r:
                    _SUPPORTED = {x["code"]: set(x.get("targets", [])) for x in json.load(r)}
            except Exception as e:
                print(f"  ! tarjima xizmatiga ulanib bo'lmadi ({e})")
    return _SUPPORTED


def route(lang, msg_id, ru):
    """Qaysi matnni qaysi tildan tarjima qilamiz: o'zbekcha to'g'ridan-to'g'ri yoki ruscha tarjima orqali."""
    sup = supported()
    if lang in sup.get("uz", set()):
        return msg_id, "uz"
    if ru.get(msg_id) and lang in sup.get("ru", set()):
        return ru[msg_id], "ru"
    return None, None


def machine(text, lang, cache, source="uz"):
    """Mashina tarjimasi (ixtiyoriy). O'rinbosarlar tarjimaga berilmaydi: ⟦0⟧, ⟦1⟧ … bilan almashtiriladi."""
    url = os.environ.get("RM_TRANSLATE_URL")
    if not url or not text:
        return None
    key = source + ":" + text
    if key in cache:
        return cache[key]
    keep = PLACEHOLDER.findall(text)
    masked = text
    for i, p in enumerate(keep):
        masked = masked.replace(p, f"⟦{i}⟧", 1)
    body = json.dumps({"q": masked, "source": source, "target": lang, "format": "text",
                       "api_key": os.environ.get("RM_TRANSLATE_KEY", "")}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            out = json.load(r).get("translatedText") or ""
    except Exception as e:  # tarmoq xatosi — satr o'zbekcha qoladi, keyingi ishga tushirishda qayta uriniladi
        print(f"  ! {lang}: tarjima xizmati javob bermadi ({e})")
        return None
    for i, p in enumerate(keep):
        if f"⟦{i}⟧" not in out:
            return None          # o'rinbosar yo'qolgan — xavfli, qo'llamaymiz
        out = out.replace(f"⟦{i}⟧", p)
    cache[key] = out
    return out


def ru_strings():
    with (ROOT / "ru" / "LC_MESSAGES" / "messages.po").open("rb") as f:
        # faqat tasdiqlangan tarjimalar: «fuzzy» (pybabel update taxmini) manba bo'la olmaydi
        return {m.id: m.string for m in read_po(f, locale="ru") if m.id and m.string and not m.fuzzy}


def run(lang):
    ru = ru_strings() if lang != "ru" else {}
    po_path = ROOT / lang / "LC_MESSAGES" / "messages.po"
    with po_path.open("rb") as f:
        cat = read_po(f, locale=lang)
    words = core(lang)
    cache_path = ROOT / lang / "mt_cache.json"
    cache = json.loads(cache_path.read_text("utf8")) if cache_path.exists() else {}
    from_dict = from_mt = 0
    for msg in cat:
        # «fuzzy» — pybabel update o'xshash eski satrdan qo'ygan taxmin; u ko'pincha noto'g'ri, shuning uchun
        # bo'sh deb hisoblanadi va qaytadan to'ldiriladi
        if msg.id and msg.fuzzy:
            msg.string = ""
            msg.flags.discard("fuzzy")
        if not msg.id or msg.string or msg.pluralizable:
            continue
        if msg.id in words:
            msg.string = words[msg.id]
            from_dict += 1
        else:
            text, source = route(lang, msg.id, ru)
            t = machine(text, lang, cache, source) if text else None
            if t:
                msg.string = t
                msg.auto_comments = list(msg.auto_comments) + [MT_NOTE]
                from_mt += 1
    if cache:
        cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=1), "utf8")
    with po_path.open("wb") as f:
        write_po(f, cat, width=0)
    with po_path.with_suffix(".mo").open("wb") as f:
        write_mo(f, cat)
    total = sum(1 for m in cat if m.id)
    done = sum(1 for m in cat if m.id and m.string)
    print(f"{lang}: lug'atdan {from_dict}, mashina tarjimasi {from_mt}. Tayyor: {done} / {total} ({done * 100 // total}%)")
    return done, total


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--extract", action="store_true", help="avval shablonlardan matnlarni yig'ish")
    ap.add_argument("--lang", choices=LANGS, help="faqat shu til")
    a = ap.parse_args()
    if a.extract:
        extract()
    for lang in ([a.lang] if a.lang else LANGS):
        run(lang)
    if not os.environ.get("RM_TRANSLATE_URL"):
        print("Eslatma: mashina tarjimasi uchun LibreTranslate'ni ishga tushiring (docker compose up -d translate) va\n"
              "  RM_TRANSLATE_URL=http://localhost:5050/translate bering.")
    elif supported():
        print("Tarjima xizmati tillari:", ", ".join(sorted(supported())),
              "— o'zbek/qoraqalpoq yo'q bo'lsa, bu tillar faqat lug'at va tarjimon orqali to'ldiriladi.")


if __name__ == "__main__":
    main()
