# Backend rejasi: kim nima qiladi

Holat: 2026-11-24, `backend` branchi.

Belgilar: ✅ tayyor, ⏳ navbatda. «Kutadi» ustunida shu bosqich sizning qaysi qadamingizga bog'liqligi ko'rsatilgan.

## A. Men bajaradigan qismlar (ketma-ket)

| № | Bosqich | Nima qilinadi | Kutadi |
|---|---|---|---|
| 1 | ✅ Baza | 26 jadval, Alembic migratsiyalari, alohida test bazasi | — |
| 2 | ✅ Kirish | Flask-Login, ro'yxatdan o'tish, parolni tiklash, profil, rollar | — |
| 3 | ✅ Testlar yadrosi | Ixcham `attempt_items`, test yig'ish servisi (`app/services/attempts.py`) | — |
| 4 | ✅ Kontentni yuklash | JSON formati ([kontent-formati.md](kontent-formati.md)), tekshiruv, `flask kontent-yuklash`, namunaviy kontent (`app/seed/namuna_kontent.json`) | — |
| 5 | ✅ O'qituvchi ekranlari bazadan (1-qism) | Mavzu sahifasi (kichik mavzular bo'yicha foizlar javoblardan), dars sahifasi `/app/dars/<id>` (bloklar bazadan), tezkor qidiruv, eslatmalar uchun mavzular ro'yxati, hududni saqlash (`app/services/catalog.py`) | — |
| 5b | ✅ O'qituvchi ekranlari (2-qism) | O'quv reja, bosh sahifa (tayyorlik, prognoz, keyingi qadam, bugungi reja, 3 qadamli yo'riqnoma), «Xatolar analitikasi», majburiy testlar jadvali, oraliq nazorat sahifasi (`app/services/plan.py`); attestatsiya sanasi `users.exam_date`dan | — |
| 6 | ✅ Test o'ynatgichi bazada | 11 tur test savollar bankidan (`app/services/test_builder.py`), pleyer, javoblarni saqlash (`/api/urinish`, oflayn qayta yuborish), bosqichlar, baholash (`app/services/scoring.py`), natija va tahlil, xatolar va mavzu holati (`app/services/progress.py`), e'tiroz yuborish/tahrirlash/o'chirish | — |
| 7 | ✅ Ekspert paneli (1-qism) | Savollar banki bazadan (filtrlar, sahifalash, «savollar yetarli emas»), muharrir: yaratish va tahrirlash (har tahrir yangi versiya, kichik mavzu tanlovi, jadval/chizma/rasm), arxivlash, AI navbati (tahrirlab tasdiqlash, rad etish), `audit_log`, rasm yuklash (PNG/JPEG/WebP, mazmunga qarab tekshiruv) | — |
| 7b | ✅ Ekspert paneli (2-qism) | «Mavzular va darslar» muharriri bazada (mavzu, dars, kichik mavzu, 9 tur blok, shablon tanlash; bir vaqtda tahrirlashdan himoya), e'tirozlarni ko'rib chiqish va natijalarni qayta hisoblash (faqat foydaga), rad etilgan AI savolini natijadan chiqarish, ixcham `notifications`, Excel eksport (import formatida, qayta yuklash takrorlamaydi), variant izohlari va kod maydoni, `expert_profiles` (huquqlar va mavzular; admin oynasi — 8-bosqichda) | — |
| 7c | ✅ Takrorlanmaslik va xotira | Ko'rilgan savollar bitmapi (`user_seen`), takroriy savol berilmaydi, shablon generator (37 ta shablon, kichik mavzuga `generators` orqali bog'lanadi), xato boshqa savol bilan tuzatiladi, `at` tozalanadi, 7 kundan eski urinishlar siqiladi (`flask eski-testlarni-siqish`; jadval bo'yicha ishga tushirish — 10-bosqichda) | — |
| 7d | ✅ Savol formatlari | Kod tili (13 ta til, serverda ranglash), HTML/CSS natijasi (skriptsiz oyna), Excel oynasi, Scratch bloklari, LOGO chizmasi, Word/Excel/PowerPoint/Paint tugmalari, variantlar kod/chizma/tugma ko'rinishida; muharrirda jonli ko'rinish; jami 68 ta shablon (`app/services/media.py`, `ui_icons.py`, `highlight.py`) | — |
| 8 | ✅ Admin paneli | Statistika va CSV hisobot, foydalanuvchilar (filtr, karta, bloklash, parol havolasi, o'chirish, CSV), attestatsiya sanasi va uni Excel'dan yuklash, ekspertlar va taklifnomalar (`expert_invites`, token bazada saqlanmaydi), huquq va mavzular, sozlamalar (`services/settings.py`), amallar jurnali, `daily_stats`, `question_stats`; `last_seen_at` kuniga bir marta yangilanadi | 5 |
| 9 | ⏳ Himoya | Kirish va kod yuborishni cheklash (IP va login bo'yicha, PostgreSQL'da), `MAX_CONTENT_LENGTH`, xavfsizlik tekshiruvi | — |
| 10 | ⏳ Fon vazifalari | PostgreSQL `jobs` navbati (`SKIP LOCKED`) va bitta worker, Redis'siz: email, audio, savol tayyorlash, statistika | — |
| 10b | ⏳ Faol bo'lmagan akkauntlar | 6 oy: 14 kun oldin ogohlantirish, o'chirish, fayllarni tozalash; ogohlantirish yuborilmagan bo'lsa o'chirilmaydi | 10, 11 yoki 12 |
| 10c | ⏳ Oflayn paket | Mavzu darslari va dars testlarini oldindan yuklash (kalitsiz), 30 MB chegara | 7c |
| 11 | ⏳ Telegram bot | Webhook orqali Flask ichida: `/start`, raqam ulashish, kod yuborish, ekspert taklifnomasi | B3 |
| 12 | ⏳ Email | Kodlar, taklifnomalar, eslatmalar (SMTP, fon vazifasi orqali) | B4 |
| 13 | ⏳ AI va RAG | OpenAI formatidagi yagona yengil mijoz va provayderlar zanjiri, `ai_cache`, limitlar; RAG: `pg_trgm` + `gemini-embedding-2` (`halfvec(768)`); bloklar bilan javob (matn, jadval, sxema, rasm), SSE; shaxsiy ma'lumotni olib tashlash | B5, B2 |
| 13b | ⏳ AI savol tuzish | Shablon yetmasa AI savol: format → o'xshashlik → ikkinchi model tekshiruvi → foydalanuvchiga beriladi va ekspertizaga tushadi | 13 |
| 14 | ⏳ Ovoz | O'qib berish: Azure `uz-UZ`, Opus, xesh bo'yicha bir marta; savolni ovozda berish (nutqni aniqlash, yozuv saqlanmaydi) | B6 |
| 15 | ⏳ Sertifikat | Bosma sahifa brauzerda PDF'ga saqlanadi (serverda PDF yo'q); `/s/<raqam>` bazadan tekshiradi; ixcham jadval (124 bayt), akkaunt o'chsa ham qoladi; ekspertizadagi savol bo'lsa kutadi | — |
| 16 | ⏳ Ishga tushirish fayllari | Gunicorn (gthread), Nginx, systemd, Postgres sozlamalari, kunlik zaxira nusxa (`pg_dump`), log va Telegram ogohlantirishlari, deploy skripti | B7, B8 |
| 17 | ⏳ Ishga tushirishdan oldin | `/ekranlar` va namunaviy akkauntlar o'chiriladi, CSP tekshiriladi, yuklama sinovi o'tkaziladi | 16 |

Talablar va tanlangan yechimlar: [talablar-va-yechimlar.md](talablar-va-yechimlar.md).

Har bir bosqich alohida commit bo'ladi va testlari bilan topshiriladi.

## B. Siz bajaradigan qismlar (ketma-ket)

Maxfiy kalitlarni (tokenlar, parollar, API kalitlar) chatga yozmang. Ular serverdagi `.env` fayliga yoziladi. Men faqat qaysi o'zgaruvchi kerakligini aytaman.

1. ✅ **Baholash qoidalari (2026-11-23 da tasdiqlangan).**
   - Ko'p javobli: (to'g'ri belgilangan − noto'g'ri belgilangan) ÷ jami to'g'ri; manfiy bo'lsa 0.
   - Moslashtirish: har bir to'g'ri juftlik uchun teng ulush.
   - Ochiq javob: `value` yoki `accept` ro'yxatidan biri; katta-kichik harf, ortiqcha bo'sh joy va tutuq belgisi yozilishi farqlanmaydi.
   - Chegaralar: < 70 — qayta o'zlashtirish, 70–89 — tavsiya bilan, ≥ 90 — o'tdi.
   - ~~Yangi savollar tugasa, eng eski ko'rilgan savol qaytadi.~~ 2026-11-24 da bekor qilindi: takroriy savol berilmaydi (7c, 13b).
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
6. **Ovoz (TTS).** 2–3 xizmatning o'zbekcha ovozini tinglab, birini tanlang (masalan, Azure uz-UZ; Meta MMS notijorat litsenziyada). Kerak bo'lsa, kalit oling.
7. **Domen.** Domen sotib oling va A yozuvini serverga yo'naltiring.
8. **Server.**
   - O'zbekiston hududidagi VPS. Shaxsiy ma'lumotlar qonuni bo'yicha fuqarolar ma'lumotlari mamlakat ichida saqlanishi kerak.
   - Tavsiya: 2 vCPU, 4 GB RAM, 40 GB SSD, Ubuntu 24.04 LTS.
   - Kirish SSH kalit orqali bo'lsin.
9. **Huquqiy matnlar.** Maxfiylik siyosati va foydalanish shartlarini yurist ko'rib chiqsin.
10. **Haqiqiy qurilmalarda sinov.** Kamida bitta iPhone va bitta Android telefonda: PWA'ni o'rnatish, oflayn test, ovoz.
11. **Birinchi admin.** Ishga tushirishda haqiqiy admin akkaunti yaratiladi, namunaviylari o'chiriladi.
12. **Kod tekshiruvi.** Har bir bosqich pull request bo'lib keladi: ko'rib chiqib, `main` ga birlashtirasiz.
13. ✅ **AI savoli (2026-11-24):** darhol beriladi va ekspertizaga tushadi; tasdiqlansa — bazaga, rad etilsa — foydalanuvchiga xabar.
14. ✅ **Sertifikat (2026-11-24):** akkaunt o'chsa ham saqlanadi, ixcham ko'rinishda.
15. **Google orqali kirish** (kod tayyor): Google Cloud Console → OAuth client ID (Web application). Qaytish manzili:
   `https://<domen>/kirish/google/qaytish` (sinov uchun `http://localhost:5000/kirish/google/qaytish`). Qiymatlar `.env` ga:
   `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`. OAuth consent screen'da maxfiylik siyosati havolasi: `/maxfiylik`.

## Bog'liqliklar qisqacha

- Bloklamaydi, hozirdanoq boshlash mumkin: A9, A10.
- B3/B4 kerak: A11/A12 (bot va email). Ungacha kod `123456` bo'lib qoladi.
- B5 kerak: A13 (AI).
- B7 va B8 kerak: A16 (serverga chiqarish).
