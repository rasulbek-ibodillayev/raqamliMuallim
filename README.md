# raqamliMuallim

Informatika o‘qituvchilarini attestatsiyaga moslashuvchan tayyorlash platformasi (PWA).

**Hozirgi holat:** frontend prototipi tayyor. Hamma ekranlar Jinja2 shablonlarida yozilgan va namunaviy ma’lumotlar bilan ishlaydi. Backend (PostgreSQL, autentifikatsiya, AI) keyingi bosqichda qo‘shiladi.

## Ishga tushirish

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Windows
.venv/Scripts/python run.py
```

Keyin brauzerda oching:
- http://localhost:5000/ekranlar — barcha ekranlar ro‘yxati
- http://localhost:5000/ — mehmon sahifasi
- http://localhost:5000/app/ — o‘qituvchi paneli

## Testlar

```bash
.venv/Scripts/pip install -r requirements-dev.txt
.venv/Scripts/python -m pytest -q
```

Testlar barcha ekranlarni (har biri o‘z roli bilan), rollar matritsasini, formalar tekshiruvini (JSON va JS’siz), CSRF, test pleyer API’sini va tarjimalarni tekshiradi.

## Rollar

O‘qituvchi (`/app`, `/test`), ekspert (`/ekspert`) va admin (`/admin`) — har biri faqat o‘z paneliga kiradi (`app/roles.py`).
Namunada rol kirishdagi login’dan aniqlanadi: `admin@…` — admin, `ekspert@…` — ekspert. `/ekranlar` havolalari rolni o‘zi almashtiradi.

## Tillar

Asosiy til o‘zbekcha; rus tili `?til=ru` yoki profil/kirish sahifasidagi UZ/RU tugmasi. Matnlar `{{ _("...") }}` ichida.

```bash
.venv/Scripts/pybabel extract -F babel.cfg -k _l -o app/translations/messages.pot --no-wrap .
.venv/Scripts/pybabel update -i app/translations/messages.pot -d app/translations --no-wrap
.venv/Scripts/python scripts/apply_translations.py   # app/translations/ru_core.py dagi tarjimalarni yozadi va kompilyatsiya qiladi
```

## Tuzilma

```
app/
  __init__.py          Flask ilova fabrikasi
  mock.py              namunaviy ma’lumotlar (keyin bazaga almashtiriladi)
  views/               blueprintlar: auth, user, test, expert, admin, meta
  templates/
    base.html          umumiy <head>, ikonkalar
    _ui.html           makroslar: icon, badge, progress, ring, code, composer…
    layouts/           app (o‘qituvchi), focus (test/dars), auth, panel (ekspert/admin)
    auth/ user/ test/ expert/ admin/ meta/
  static/
    css/app.css        dizayn tizimi (tokenlar, komponentlar, yorug‘/qorong‘i rejim)
    js/app.js          kichik yordamchilar (taymer, OTP, kod ranglash, nusxa olish)
design/stitch-reference/   Google Stitch eksporti: 82 ekran bo‘limlarga ajratilgan + DESIGN.md
docs/usability-test-plan.md  5 nafar o‘qituvchi bilan sinov rejasi (vazifalar, kuzatuv varag‘i, SUS)
```

## Dizayn tamoyillari

- **Minimalizm:** soyalar yo‘q, faqat 1px chegaralar; bitta asosiy rang (`#2563EB`); har sahifada bitta asosiy tugma.
- **AI muhit:** bosh sahifa va AI tutor chat ko‘rinishida (so‘rov maydoni, taklif chiplari); AI elementlari alohida gradient belgi bilan ajratiladi.
- **Mobil birinchi:** telefonda pastki menyu va markazda AI tutor tugmasi; desktopda chap panel.
- **Fokus rejimi:** test va dars sahifalarida menyu yo‘q, asosiy harakat pastda turadi.
- Holat ranglari doim belgi bilan birga (✓ / ✗), rangni ajrata olmaydiganlar uchun ham tushunarli.
- Yorug‘ va qorong‘i mavzu.

## Keyingi qadamlar

1. SQLAlchemy modellari va Alembic migratsiyalari (TZ 23-bo‘lim).
2. Telegram/email orqali ro‘yxatdan o‘tish va sessiyalar.
3. `mock.py` o‘rniga servis qatlami; formalarni HTMX bilan ulash.
4. ~~Test javoblarini IndexedDB'ga yozib, internet tiklanganda yuborish.~~ Tayyor (`static/js/player.js`, `/api/urinish`); backendda API saqlashni bazaga o‘tkazish qoldi.
5. Eslatmalar, bildirishnomalar va qidiruvni brauzer xotirasi va namunaviy ma’lumot o‘rniga API'ga ulash.
6. Rus tili tarjimasini to‘ldirish (hozir ~34%: menyu, kirish, xatolar, testlar; dars matnlari va maxfiylik siyosati — tarjimonga).

Alpine.js (`static/vendor/`) va Inter shrifti (`static/fonts/`) loyiha ichida — asosiy sahifalar tashqi serverlarsiz ishlaydi.
