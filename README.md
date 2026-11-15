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
4. Test javoblarini IndexedDB'ga yozib, internet tiklanganda yuborish (Service Worker allaqachon bor: `app/static/sw.js`).
5. Konspekt, bildirishnomalar va qidiruvni brauzer xotirasi va namunaviy ma’lumot o‘rniga API'ga ulash.

Alpine.js (`static/vendor/`) va Inter shrifti (`static/fonts/`) loyiha ichida — asosiy sahifalar tashqi serverlarsiz ishlaydi.
