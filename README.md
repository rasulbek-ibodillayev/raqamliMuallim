# raqamliMuallim

Informatika o‘qituvchilarini attestatsiyaga moslashuvchan tayyorlash platformasi (PWA).

**Hozirgi holat:** frontend prototipi tayyor. Hamma ekranlar Jinja2 shablonlarida yozilgan va namunaviy ma’lumotlar bilan ishlaydi. Backend (PostgreSQL, autentifikatsiya, AI) keyingi bosqichda qo‘shiladi.

## Ishga tushirish

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Windows
.venv/Scripts/python run.py
```

Ma’lumotlar bazasi (PostgreSQL 16 + pgvector, Docker Desktop kerak):

```bash
docker compose up -d db
FLASK_APP=run.py .venv/Scripts/flask db upgrade
```

Boshqa bazaga ulanish uchun `DATABASE_URL` muhit o‘zgaruvchisini bering. Kirish, ro‘yxatdan o‘tish va profil bazaga yozadi,
qolgan ekranlar hozircha `mock.py` dan o‘qiydi.

Namunaviy akkauntlar (parol `parol1234`, maxfiy so‘z «informatika»):

```bash
FLASK_APP=run.py .venv/Scripts/flask namuna-foydalanuvchilar
```

| Rol | Login |
|-----|-------|
| o‘qituvchi | +998 90 123 45 67 |
| ekspert | ekspert@raqamlimuallim.uz |
| admin | admin@raqamlimuallim.uz |

`/ekranlar` va `/_rol/<rol>` faqat debug rejimida (`run.py`) yoki `RM_DEV_TOOLS=1` bilan ochiladi.

Testlar alohida bazada ishlaydi (bir marta yarating):

```bash
docker exec raqamlimuallim-db-1 psql -U raqamli -d raqamli -c "CREATE DATABASE raqamli_test"
.venv/Scripts/python -m pytest -q
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

Asosiy til o‘zbekcha; rus va ingliz tillari — `?til=ru|en` yoki yuqoridagi til tanlash ro'yxati. Matnlar `{{ _("...") }}` ichida.

Kataloglarni yangilash va tarjima qilish uchun dastur — `scripts/translate.py`:

```bash
.venv/Scripts/python scripts/translate.py --extract   # yangi matnlarni yig'ish + lug'atdan to'ldirish + kompilyatsiya
```

Lug'atlar: `app/translations/ru_core.py`, `core_en.py`. Qolgan satrlar uchun `RM_TRANSLATE_URL`
(LibreTranslate bilan mos API) va `RM_TRANSLATE_KEY` berilsa, mashina tarjimasi qo'shiladi va «mashina tarjimasi» deb belgilanadi.
Tarjima qilinmagan satr o‘zbekcha ko‘rinadi.

## Tuzilma

```
app/
  __init__.py          Flask ilova fabrikasi
  extensions.py        SQLAlchemy va Flask-Migrate
  models/              ma’lumotlar modeli, 26 jadval (TZ 23: docs/tz-23-malumotlar-modeli.md)
  mock.py              namunaviy ma’lumotlar (keyin bazaga almashtiriladi)
  views/               blueprintlar: auth, user, test, expert, admin, meta
  templates/
    base.html          umumiy <head>, ikonkalar
    _ui.html           makroslar: icon, badge, progress, ring, code, composer…
    layouts/           app (o‘qituvchi), focus (test/dars), auth, panel (ekspert/admin)
    auth/ user/ test/ expert/ admin/ meta/
  static/
    css/app.css        dizayn tizimi (tokenlar, komponentlar, yorug‘/qorong‘i rejim)
    js/core.js         har sahifada: formalar (rmForm), tarjima (rmT), toast, OTP, kod ranglash, nusxa olish
    js/learner.js      o'qituvchi qobig'i: menyu/qidiruv, ilovani o'rnatish, dam olish taymeri
    js/lesson.js       dars sahifasi · js/tutor.js — AI tutor · js/test.js — test va attestatsiya
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

1. ~~SQLAlchemy modellari va Alembic migratsiyalari (TZ 23-bo‘lim).~~ Tayyor; `questions` maydonlari TZ 6.1 bilan solishtirilishi kerak.
2. ~~Ro‘yxatdan o‘tish va sessiyalar.~~ Flask-Login va `users` jadvali ulandi; Telegram bot va email orqali kod yuborish
   (hozir kod har doim 123456), kirish urinishlarini cheklash va ekspert taklifnomalari jadvali qoldi.
3. `mock.py` o‘rniga servis qatlami; formalarni HTMX bilan ulash.
4. ~~Test javoblarini IndexedDB'ga yozib, internet tiklanganda yuborish.~~ Tayyor (`static/js/player.js`, `/api/urinish`); backendda API saqlashni bazaga o‘tkazish qoldi.
5. Eslatmalar, bildirishnomalar va qidiruvni brauzer xotirasi va namunaviy ma’lumot o‘rniga API'ga ulash.
6. Rus tili tarjimasini to‘ldirish (hozir ~34%: menyu, kirish, xatolar, testlar; dars matnlari va maxfiylik siyosati — tarjimonga).

Alpine.js (`static/vendor/`) va Inter shrifti (`static/fonts/`) loyiha ichida — asosiy sahifalar tashqi serverlarsiz ishlaydi.
