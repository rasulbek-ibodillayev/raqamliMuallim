# Backend rejasi: kim nima qiladi

Holat: 2026-11-23, `backend` branchi.

Belgilar: ✅ tayyor, ⏳ navbatda. «Kutadi» ustunida shu bosqich sizning qaysi qadamingizga bog'liqligi ko'rsatilgan.

## A. Men bajaradigan qismlar (ketma-ket)

| № | Bosqich | Nima qilinadi | Kutadi |
|---|---|---|---|
| 1 | ✅ Baza | 26 jadval, Alembic migratsiyalari, alohida test bazasi | — |
| 2 | ✅ Kirish | Flask-Login, ro'yxatdan o'tish, parolni tiklash, profil, rollar | — |
| 3 | ✅ Testlar yadrosi | Ixcham `attempt_items`, `user_seen_questions`, test yig'ish servisi (`app/services/attempts.py`) | — |
| 4 | ✅ Kontentni yuklash | JSON formati ([kontent-formati.md](kontent-formati.md)), tekshiruv, `flask kontent-yuklash`, namunaviy kontent (`app/seed/namuna_kontent.json`) | — |
| 5 | ✅ O'qituvchi ekranlari bazadan (1-qism) | Mavzu sahifasi (kichik mavzular bo'yicha foizlar javoblardan), dars sahifasi `/app/dars/<id>` (bloklar bazadan), tezkor qidiruv, eslatmalar uchun mavzular ro'yxati, hududni saqlash (`app/services/catalog.py`) | — |
| 5b | ⏳ O'qituvchi ekranlari (2-qism) | O'quv reja, bosh sahifa, «Xatolar analitikasi» va majburiy testlar jadvali (qachon navbati kelishi). «Natijalarim», natija tafsiloti va diagnostika natijasi 6-bosqichda bazaga o'tdi | — |
| 6 | ✅ Test o'ynatgichi bazada | 11 tur test savollar bankidan (`app/services/test_builder.py`), pleyer, javoblarni saqlash (`/api/urinish`, oflayn qayta yuborish), bosqichlar, baholash (`app/services/scoring.py`), natija va tahlil, xatolar va mavzu holati (`app/services/progress.py`), e'tiroz yuborish/tahrirlash/o'chirish | — |
| 7 | ✅ Ekspert paneli (1-qism) | Savollar banki bazadan (filtrlar, sahifalash, «savollar yetarli emas»), muharrir: yaratish va tahrirlash (har tahrir yangi versiya, kichik mavzu tanlovi, jadval/chizma/rasm), arxivlash, AI navbati (tahrirlab tasdiqlash, rad etish), `audit_log`, rasm yuklash (PNG/JPEG/WebP, mazmunga qarab tekshiruv) | — |
| 7b | ⏳ Ekspert paneli (2-qism) | «Mavzular va darslar» muharriri bazaga (bo'lim, mavzu, kichik mavzu, bloklar), Excel import/eksport, ekspert huquqlari (yo'nalishlar, ruxsatlar); e'tirozlarni ko'rib chiqish va natijani qayta hisoblash | — |
| 8 | ⏳ Admin paneli | Foydalanuvchilar, sozlamalar (`settings`), imtihon sanasi, `expert_invites` jadvali, `audit_log`, Excel/CSV import va eksport | 5 |
| 9 | ⏳ Himoya | Redis, kirish va kod yuborishni cheklash (IP va login bo'yicha), xavfsizlik tekshiruvi | — |
| 10 | ⏳ Fon vazifalari | Redis + RQ (`volatile-lru`, 64 MB): email, audio, PDF, statistika | — |
| 11 | ⏳ Telegram bot | Webhook orqali Flask ichida: `/start`, raqam ulashish, kod yuborish, ekspert taklifnomasi | B3 |
| 12 | ⏳ Email | Kodlar, taklifnomalar, eslatmalar (SMTP, fon vazifasi orqali) | B4 |
| 13 | ⏳ AI va RAG | Provayderlar zanjiri, `ai_cache`, `ai_usage`, oylik limit; tutor javobini oqim bilan uzatish (SSE); RAG: hujjatlarni bo'laklash, `halfvec` embeddinglar, o'xshashlik chegarasi | B5, B2 |
| 14 | ⏳ Ovoz (TTS) | Blok matni xeshi bo'yicha bir marta yaratish, Opus/AAC, `audio_assets` | B6 |
| 15 | ⏳ Sertifikat PDF | WeasyPrint fon vazifasida, bir marta yaratib saqlash; `/s/<raqam>` bazadan tekshiradi | 6 |
| 16 | ⏳ Ishga tushirish fayllari | Gunicorn (gthread), Nginx, systemd, Postgres sozlamalari, kunlik zaxira nusxa (`pg_dump`), log va Telegram ogohlantirishlari, deploy skripti | B7, B8 |
| 17 | ⏳ Ishga tushirishdan oldin | `/ekranlar` va namunaviy akkauntlar o'chiriladi, CSP tekshiriladi, yuklama sinovi o'tkaziladi | 16 |

Har bir bosqich alohida commit bo'ladi va testlari bilan topshiriladi.

## B. Siz bajaradigan qismlar (ketma-ket)

Maxfiy kalitlarni (tokenlar, parollar, API kalitlar) chatga yozmang. Ular serverdagi `.env` fayliga yoziladi. Men faqat qaysi o'zgaruvchi kerakligini aytaman.

1. ✅ **Baholash qoidalari (2026-11-23 da tasdiqlangan).**
   - Ko'p javobli: (to'g'ri belgilangan − noto'g'ri belgilangan) ÷ jami to'g'ri; manfiy bo'lsa 0.
   - Moslashtirish: har bir to'g'ri juftlik uchun teng ulush.
   - Ochiq javob: `value` yoki `accept` ro'yxatidan biri; katta-kichik harf, ortiqcha bo'sh joy va tutuq belgisi yozilishi farqlanmaydi.
   - Chegaralar: < 70 — qayta o'zlashtirish, 70–89 — tavsiya bilan, ≥ 90 — o'tdi.
   - Yangi savollar tugasa, eng eski ko'rilgan savol qaytadi.
   - Dars testi 3 savol, kamida bittasi ko'p javobli yoki moslashtirish (aks holda 70–89% chiqishi mumkin emas).
   - Bosqichli testda mavzu bo'yicha: < 70% — keyingi bosqichga o'tmaydi; 70–89% — o'tadi, 90% ga yetmagan darslarini qayta o'zlashtirish tavsiya etiladi; ≥ 90% — tavsiyasiz o'tadi. Berilmagan savollar 0 ball.
2. **Kontent.**
   - Har bir darsga kamida 3 ta savol, ulardan kamida bittasi ko'p javobli yoki moslashtirish.
   - Haqiqiy savollar bazasi va dars matnlari, [kontent-formati.md](kontent-formati.md) dagi JSON formatida.
   - RAG uchun darsliklar va me'yoriy hujjatlar. Ulardan foydalanish huquqi bo'lishi kerak.
3. **Telegram bot.** @BotFather orqali bot yarating va bot nomini ayting. Tokenni serverdagi `.env` ga `TELEGRAM_BOT_TOKEN` sifatida yozasiz.
4. **Email.**
   - Domen pochtasi yoki SMTP xizmatini tanlang.
   - Domenga SPF, DKIM va DMARC yozuvlarini qo'shing, aks holda xatlar spamga tushadi.
   - SMTP ma'lumotlari `.env` ga yoziladi.
5. **AI kaliti.**
   - Provayderni tanlang (masalan, Gemini) va API kalit oling.
   - Qaror qabul qiling: bepul tarifmi yoki pullik? Bepul tarifda yuborilgan matnlar provayder tomonidan ishlatilishi mumkin.
   - Oylik xarajat chegarasini belgilang.
6. **Ovoz (TTS).** 2–3 xizmatning o'zbekcha ovozini tinglab, birini tanlang (masalan, Azure uz-UZ yoki ochiq Meta MMS-TTS). Kerak bo'lsa, kalit oling.
7. **Domen.** Domen sotib oling va A yozuvini serverga yo'naltiring.
8. **Server.**
   - O'zbekiston hududidagi VPS. Shaxsiy ma'lumotlar qonuni bo'yicha fuqarolar ma'lumotlari mamlakat ichida saqlanishi kerak.
   - Tavsiya: 2 vCPU, 4 GB RAM, 40 GB SSD, Ubuntu 24.04 LTS.
   - Kirish SSH kalit orqali bo'lsin.
9. **Huquqiy matnlar.** Maxfiylik siyosati va foydalanish shartlarini yurist ko'rib chiqsin.
10. **Haqiqiy qurilmalarda sinov.** Kamida bitta iPhone va bitta Android telefonda: PWA'ni o'rnatish, oflayn test, ovoz.
11. **Birinchi admin.** Ishga tushirishda haqiqiy admin akkaunti yaratiladi, namunaviylari o'chiriladi.
12. **Kod tekshiruvi.** Har bir bosqich pull request bo'lib keladi: ko'rib chiqib, `main` ga birlashtirasiz.

## Bog'liqliklar qisqacha

- Bloklamaydi, hozirdanoq boshlash mumkin: A4, A5, A7, A8, A9, A10.
- B3/B4 kerak: A11/A12 (bot va email). Ungacha kod `123456` bo'lib qoladi.
- B5 kerak: A13 (AI).
- B7 va B8 kerak: A16 (serverga chiqarish).
