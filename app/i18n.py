"""Ko'p tillilik (Flask-Babel).

- Asosiy til — o'zbekcha (lotin). Shablon matnlari `{{ _("...") }}` ichida; msgid — o'zbekcha matnning o'zi.
- Rus, ingliz va qoraqalpoq tillari: app/translations/<til>/LC_MESSAGES/messages.po. Tarjima qilinmagan satr o'zbekcha ko'rinadi.
- Til tanlash: ?til=uz|ru|en|kaa (sessiyada eslab qolinadi), keyin sessiya, keyin standart (uz).
- Kataloglarni to'ldirish va kompilyatsiya: scripts/translate.py (lug'at + ixtiyoriy mashina tarjimasi).

Yangi matn qo'shilganda:
    .venv/Scripts/pybabel extract -F babel.cfg -o app/translations/messages.pot .
    .venv/Scripts/pybabel update -i app/translations/messages.pot -d app/translations
    (ru/messages.po ni tarjima qilish)
    .venv/Scripts/pybabel compile -d app/translations

Eslatma: Jinja "newstyle" gettext har bir satrni %-formatlaydi, shuning uchun matndagi foiz belgisi `%%` deb yoziladi.
"""
from flask import request, session
from flask_babel import Babel

LANGS = {"uz": "O‘zbekcha", "ru": "Русский", "en": "English", "kaa": "Qaraqalpaqsha"}
# Tugmadagi qisqa nom (kaa — ISO 639 kodi, foydalanuvchiga «QQ» deb ko'rsatiladi)
SHORT = {"uz": "UZ", "ru": "RU", "en": "EN", "kaa": "QQ"}
DEFAULT = "uz"


def select_locale() -> str:
    lang = request.args.get("til")
    if lang in LANGS:
        session["til"] = lang
        return lang
    lang = session.get("til")
    return lang if lang in LANGS else DEFAULT


def init_app(app):
    app.config.setdefault("BABEL_DEFAULT_LOCALE", DEFAULT)
    app.config.setdefault("BABEL_TRANSLATION_DIRECTORIES", "translations")
    Babel(app, locale_selector=select_locale)

    @app.context_processor
    def inject_lang():
        from flask_babel import get_locale
        return {"current_lang": str(get_locale() or DEFAULT), "langs": LANGS, "lang_short": SHORT}
