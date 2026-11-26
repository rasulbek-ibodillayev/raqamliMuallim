# Talablar va tanlangan yechimlar

Holat: 2026-11-24. Talablar — buyurtmachidan; yechimlar — taklif. ❓ savollarga
2026-11-24 da javob berildi (5, 7-bo'limlar va 2-bo'limdagi suhbat). O'lchovlar shu kuni vaqtinchalik PostgreSQL 16 bazasida olingan (500 foydalanuvchi × 2000 javob = 1 mln javob,
20 000 savol).

## Umumiy tamoyil

Arzon va aniq manba birinchi, AI — oxirida: **baza → shablon generator → kesh → bepul AI**. Har bir narsa bir marta
yaratiladi va xeshi bo'yicha qayta ishlatiladi.

## 1. Xotirani tejash

| Nima | Hozir | Taklif | Farqi |
|---|---|---|---|
| Ko'rilgan savollar ✅ | Avval: har juftlikka qator | Foydalanuvchiga bitta bitmap (`bytea`, bit = savol id) | 72 → 1,44 MB (50 baravar; kodda o'lchandi) |
| Javoblar ✅ | `{"v":…, "at":…}` | Test yakunlangach faqat `v` qoladi (`at` faqat sinxronlash paytida kerak) | 139 → 114 MB (−18%) |
| Eski urinishlar ✅ | Ustun bor, kod yo'q | 7 kundan eskisi `items_archive`ga siqiladi (avval 12 oy, zlib edi) | 20 savol ≈ 124 bayt; 1 mln javob 139 → ≈ 11 MB |
| RAG vektorlari | `vector(768)`, 4 bayt/o'lcham | `halfvec(768)`, 2 bayt/o'lcham | vektor hajmi 2 baravar kam |
| Navbat va cheklovlar ✅ | Reja: Redis + RQ | PostgreSQL `jobs` va `rate_limits`; worker veb-jarayon ichida | Redis yo'q; alohida worker ≈ 90 MB o'rniga +2 MB (o'lchandi) |
| Sertifikat PDF | Reja: WeasyPrint serverda | Brauzerning «PDF'ga chop etish»i (sahifa tayyor) | Server kutubxonalari va PDF fayllar yo'q |
| Tarjima | LibreTranslate ≈ 200 MB RAM, obraz 2,1 GB | Faqat ishlab chiqishda; serverga chiqarilmaydi | −200 MB RAM |

Bitmap faqat «takrorlanmasin» qoidasi uchun yetadi: savol endi hech qachon qaytarilmagani sababli `seen_on` sanasi kerak emas.

7c bajarildi (2026-11-24). Kodda o'lchandi (20 000 savol, 500 foydalanuvchi × 2000): bitta kichik mavzudan tanlash 4,7 ms,
butun bank bo'yicha hisob 17 ms, 35 savollik attestatsiya testini tuzish 58 ms, diagnostika 122 ms, shablondan 3 ta savol 8 ms.

### Saqlash texnologiyalari (2026-11-24, qaror)

Asosiy va yagona baza — **PostgreSQL**. Bir xil ma'lumot (1 mln javob = 50 000 test × 20 savol) har birida o'lchandi:

| Texnologiya | Disk | RAM | Qaror |
|---|---|---|---|
| PostgreSQL, oddiy qatorlar | 110 MB | — | Yakunlanmagan va oxirgi 7 kunlik testlar |
| PostgreSQL + o'z ikkilik arxivimiz | ≈ 6 MB | — | **Tanlandi**: 7 kundan keyin |
| DuckDB | 10 MB | +32 MB | Yo'q: kattaroq va har worker'da RAM; statistikaga PostgreSQL yetadi |
| SQLite | 20 MB | +2 MB | Yo'q: bir vaqtda bitta yozuvchi, vektor qidiruv yo'q |
| CSV | 28 MB | — | Faqat eksport/import |
| JSON | — | — | JSONB maydonlar va kontent fayli |
| TinyDB | 31 MB | butun fayl RAM'da | Yo'q: bir vaqtda yozishda buziladi |
| MessagePack | 20 savol 133 bayt (zlib bilan) | +0,7 MB | Yo'q: o'z formatimiz 124 bayt, kutubxonasiz, 0,015 ms/test |
| LMDB, RocksDB / LevelDB | — | — | Yo'q: kesh uchun ikkinchi baza (alohida zaxira, tranzaksiya yo'q); Windows va Python 3.15 da tayyor paketi ishlamadi, o'lchanmadi |

Kiritilgan o'zgarishlar va natija (20 000 savol, 500 foydalanuvchi, 1 mln javob, indekslar bilan):

| Jadval | Avval | Keyin | Nima qilindi |
|---|---|---|---|
| attempt_items + test_attempts | 123 MB | 25 MB | 7 kundan keyin ikkilik arxiv (20 savol ≈ 124 bayt), 2 ta ortiqcha indeks olindi |
| error_items | 23 MB | 5 MB | Tuzatilgan xato o'chadi, 3 indeks o'rniga 1 ta |
| audit_log | 13 MB | 3,3 MB | Savolning to'liq nusxalari o'rniga o'zgargan maydonlar nomi |
| question_versions | 9,8 MB | 1,9 MB | Joriy versiya matni takrorlanmaydi |
| **Jami** | **177 MB** | **44 MB** | 4 baravar kam |

Worker RAM: 106 → 91 MB (Alembic faqat `flask` buyruqlarida, numpy'siz `halfvec` turi). Sifat: hamma natija saqlanadi, sahifalar
bir xil; natija tahlili arxivdan 4,6 ms, jadvaldan 4,1 ms.

## 2. AI tutor: RAG va bepul AI

**Javob tartibi:** kesh (`ai_cache`) → RAG qidiruv → model → kesh. Bir xil savolga ikkinchi marta token sarflanmaydi.

**Qidiruv:** PostgreSQL matnli qidiruvi (`pg_trgm`) + `gemini-embedding-2`, 768 o'lcham, `halfvec`. Embedding xizmati ishlamasa,
matnli qidiruvning o'zi yetadi. `text-embedding-004` (modelda yozilgani) 2026-01-14 da o'chirilgan.

**Provayderlar zanjiri** (limit tugasa — keyingisi):

| # | Provayder | Bepul limit | Izoh |
|---|---|---|---|
| 1 | Gemini 3.5 Flash-Lite | Rasmiy sahifada raqam yo'q; mustaqil manbalar ≈ 500 so'rov/kun | O'zbekiston ro'yxatda bor. Aniq limit — AI Studio'da |
| 2 | Gemma 4 (Gemini API) | Mustaqil manbalar ≈ 14 400 so'rov/kun | Soddaroq savollar, savol tuzish |
| 3 | Groq (gpt-oss-120b, qwen) | Sahifada 1000 so'rov, 200 ming token/kun/model | Bepul tarif raqami ekani tasdiqlanmagan |
| 4 | Cloudflare Workers AI | 10 000 neyron/kun (rasmiy) | Kichik modellar |
| 5 | Modelsiz | Cheksiz | Darslikdan topilgan parchalar va havola |

**Qaror (2026-11-24): yagona OpenAI formati va provayderlar zanjiri (buyurtmachi taklifi), ikki tasdiqlangan tuzatish bilan:**

1. *Kutubxona:* `openai` paketi +45,8 MB RAM va 1,4–1,9 s yuklanish, `httpx` +15 MB, standart `urllib` +8,5 MB (o'lchandi, har bir
   worker uchun). Format bir xil bo'lgani uchun kichik o'z mijozimiz yetadi: `POST {base_url}/chat/completions`, bitta modul.
2. *Kalitlarni aylantirish:* bitta provayderda bir nechta kalit limitni oshirmaydi va shartlarga zid bo'lishi mumkin. Gemini — limit loyihaga,
   Groq — tashkilotga bog'langan; OpenRouter qo'shimcha kalit va akkaunt ta'sir qilmasligini yozgan va ko'p akkaunt ochishni taqiqlaydi;
   Google API shartlari limitni chetlab o'tishni taqiqlaydi. Shuning uchun har provayderga bitta rasmiy kalit, aylanish **provayder va
   modellar** orasida. Kalit almashtirish (eskisini bekor qilish) `.env` orqali.

| Provayder | `base_url` | Holati |
|---|---|---|
| Gemini / Gemma | `https://generativelanguage.googleapis.com/v1beta/openai` | Chat, oqim, JSON sxema, embedding; OpenAI qatlami «beta» |
| Groq | `https://api.groq.com/openai/v1` | Chat; `n=1`, `logprobs` yo'q |
| Mistral | `https://api.mistral.ai/v1` | So'rov shakli mos; bepul rejim matnni o'qitishga ishlatishi mumkin (o'chirib qo'yiladi); limiti tasdiqlanmagan |
| OpenRouter | `https://openrouter.ai/api/v1` | `:free` modellar: 20/daq, 50/kun (10 kredit olinsa 1000/kun). Faqat `:free` modellar: pullikka tushsa pul yechiladi |
| Cloudflare | `https://api.cloudflare.com/client/v4/accounts/<id>/ai/v1` | Chat, embedding; 10 000 neyron/kun |
| Cerebras | `https://api.cerebras.ai/v1` | Ro'yxatga kirmaydi: doimiy bepul tarif yo'q (karta bilan $5, 30 kun) |

Zanjir qoidasi: 429/5xx/timeout — provayder `Retry-After`gacha (bo'lmasa 60 s, ikki baravar oshib) chetlatiladi va keyingisiga o'tiladi;
401/403 — o'chiriladi va adminga xabar; 400 — qayta yuborilmaydi. Holat (chetlatish, kunlik hisob) PostgreSQL'da, worker'lar uchun umumiy.
Ro'yxat `settings`da: yangi provayder kodsiz qo'shiladi. Javob JSON sxema bo'yicha tekshiriladi, mos kelmasa keyingi provayder.

**Maxfiylik.** Bepul Gemini shartlari: yuborilgan matn mahsulotni yaxshilashga ishlatiladi va odam o'qishi mumkin, shaxsiy
ma'lumot yuborish mumkin emas, foydalanuvchi 18 yoshdan katta bo'lishi kerak. Shuning uchun modelga faqat savol, mavzu va
darslik parchasi ketadi; ism, telefon, email va raqamlar avtomatik olib tashlanadi. Chegaradan tashqariga uzatish bo'yicha
2026-yilgi qonun o'zgarishlarini yurist tekshirishi kerak.

**O'qitish shakllari.** Model HTML emas, dars bloklari bilan bir xil JSON bloklar qaytaradi (matn, kod, jadval, sxema); server
tekshirib, tayyor shablonlarda chizadi.

| Shakl | Yechim | Xotira |
|---|---|---|
| Matn | Oqim (SSE) | — |
| Jadval | JSON → HTML jadval | ≈ 0,2 KB |
| Grafika, sxema | JSON tavsif → brauzerda SVG (o'zimizning kichik chizuvchi; Mermaid kutubxonasi og'ir) | ≈ 0,3 KB |
| Rasm | Kutubxonadan tanlanadi (RAG manbasi yoki ekspert yuklagan); AI rasm yaratmaydi | WebP ≤ 40 KB, xesh bo'yicha bitta nusxa |
| Ovoz (o'qib berish) | Azure `uz-UZ` Madina / Sardor, oyiga 0,5 mln belgi bepul; Opus 24 kbit/s, xesh bo'yicha bir marta | ≈ 180 KB/daqiqa |
| Ovoz (savol berish) | Groq Whisper yoki Azure `uz-UZ` nutqni aniqlash; yozuv saqlanmaydi | 0 |

Meta MMS o'zbekcha ovozi CC-BY-NC litsenziyada, tijoratda ishlatib bo'lmaydi. Ovoz sifati o'zbek tilida hali tinglab ko'rilmagan.

**Suhbat (qaror 2026-11-24, bajarildi).** Faqat qurilmadagi `localStorage`da; serverga yozilmaydi. Birinchi xabardan 24 soat o'tganda
yoki o'quv rejadagi mavzu almashganda o'zi o'chadi (sahifa ochiq turgan bo'lsa ham). Eski mavzu darsini ochib ko'rish suhbatni
o'chirmaydi. `ai_cache`ga erkin suhbat emas, faqat umumiy so'rovlar (dars izohi, savol tahlili) tushadi.

**Limitlar:** foydalanuvchiga kuniga 20 ta tutor savoli (sozlamada); kesh javoblari hisobga kirmaydi.

**«Yechimini ko'rish» (Tuzatish 24.11.2).** Natijadagi xato savoldan AI tutorga o'tiladi. Yechim tartibi: baza izohi va variant
izohlari (`answer.notes`) → shablon savolda hisob-kitob → (13-bosqich) AI. Hozir AI ulanmagan: izohi yo'q savolda to'g'ri javob va
«izoh hali yozilmagan» chiqadi. AI ulanganda yechim savolga bog'lanadi (`ai_cache`, savol id + versiya): bitta savol uchun model bir
marta chaqiriladi va hammaga ko'rsatiladi. Hisoblash savolida — yechish usuli qadam-baqadam, nazariy savolda — har bir javob izohi va
to'g'ri javobning isboti. Bazadagi kalitga zid yechim ko'rsatilmaydi. Yechim faqat yakunlangan o'z testida ochiladi.

**Google orqali ro'yxatdan o'tish.** OAuth 2.0 + PKCE, qo'shimcha kutubxonasiz (`urllib`). Parol va maxfiy so'z so'ralmaydi: ism, hudud,
rozilik. Akkaunt `users.google_sub` ga bog'lanadi (Google'da email o'zgarsa ham). Shu emailli akkaunt avvaldan bo'lsa, bir marta parol
bilan kirgandan keyin bog'lanadi: aks holda birovning emailini oldindan ro'yxatdan o'tkazgan odam uning akkauntiga kirib qolishi mumkin.

## 3. Attestatsiya savollari: dasturlar bo'yicha

Rasm o'rniga tavsif saqlanadi. **Bajarildi (7d):** server HTML/SVG chizadi (pleyer, attestatsiya, natija, AI tutor va oflaynda bir xil,
brauzerga kutubxona yuklanmaydi). Tugma ikonkalari — o'zimiz chizgan bitta umumiy to'plam.

| Dastur | Saqlanadigan narsa | Ko'rsatish | ≈ hajm |
|---|---|---|---|
| Python, JavaScript | `code` + `lang` | Sintaksis ranglari (hozir faqat Python) | 0,1–0,3 KB |
| HTML, CSS | `code` + `lang` | Kod va natija: `sandbox` iframe, skriptlarsiz | 0,2 KB |
| Excel | Katak JSON'i va formula | Jadval panjarasi, formula qatori | 0,3 KB |
| Scratch | Matnli blok yozuvi | SVG bloklar | 0,2 KB |
| LOGO | Buyruqlar matni | Brauzerda toshbaqa chizmasi (SVG) | 0,1 KB |
| Word, PowerPoint, Paint | Tugma/menyu kodi (`ui: "word.bold"`) | Bitta umumiy SVG ikonka to'plami (o'zimiz chizgan) | 0,1 KB |
| Boshqa dasturlar | Zarur bo'lsa skrinshot | WebP ≤ 40 KB | 40 KB |

Solishtirish: 20 000 savolning har biri 40 KB rasm bo'lsa ≈ 800 MB; tavsif ko'rinishida ≈ 5 MB (hisob).

## 4. Test natijalari saqlanadi

Hozir ham har bir yakunlangan urinish va har bir javob bazada. Qo'shiladi: 12 oydan eskisini siqish (natija sahifasi arxivdan
ham o'qiydi), kunlik zaxira nusxa. Bekor qilingan ixtiyoriy test natija hisoblanmaydi (javoblari o'chadi).

## 5. Savol takrorlanmaydi; tugasa — yangi savol tuziladi

Avvalgi qaror («eng eski ko'rilgan savol qaytadi») bekor bo'ladi.

Holat: 1 va 2 bajarildi (7c), 3 — 13b-bosqichda; ungacha savol ham, shablon ham qolmasa, test qisqaroq bo'ladi yoki ochilmaydi.

1. **Baza:** ko'rilmagan tasdiqlangan savollar.
2. **Shablon generator** (68 ta shablon, `app/services/question_templates.py`): parametrli savol (Python, sanoq sistemasi, Excel formulasi, LOGO…) yangi sonlar bilan. Javob kod bilan
   hisoblanadi, shuning uchun darhol `approved`; AI va token kerak emas.
3. **AI tutor:** shu kichik mavzu, daraja va turdagi savol, RAG manbasi bilan. Tekshiruv: format (`check_question`) → o'xshash savol
   yo'qligi (`pg_trgm`) → ikkinchi model kalitni ko'rmasdan yechadi, javob mos kelishi shart. O'tsa — savollar bazasiga yoziladi.
4. Baribir yetmasa — test qisqaroq beriladi va fon vazifasi yangi savol tayyorlaydi. Takroriy savol hech qachon berilmaydi.

Tugashini kutmaymiz: kichik mavzuda foydalanuvchiga 2 ta testga yetadigan yangi savol qolganda fon vazifasi oldindan to'ldiradi.

**Qaror (2026-11-24): AI savoli darhol beriladi va bir vaqtda ekspertizaga tushadi.**

| Bosqich | Nima bo'ladi |
|---|---|
| Savol tugadi | AI savol tuzadi, avtomatik tekshiruvdan o'tadi, `status=review`, `source=ai` bilan saqlanadi va shu foydalanuvchiga beriladi. Boshqalarga berilmaydi: test faqat `approved` savollarni oladi |
| Ekspert tasdiqladi | `approved`: savollar bazasiga o'tadi, hammaga tushadi |
| Ekspert rad etdi | Savol arxivlanadi, shu savol berilgan foydalanuvchiga bildirishnoma boradi |

Rad etilgan savol natijadan chiqariladi va foiz qayta hisoblanadi; natija faqat foydalanuvchi foydasiga o'zgaradi (pasaymaydi).
Bildirishnomada eski va yangi foiz ko'rsatiladi. Bildirishnoma ixcham saqlanadi: matn emas, turi va havola id'si; 30 kundan keyin
o'chadi. Yakuniy diagnostikada ekspertizadagi savol bo'lsa, sertifikat ekspertiza tugagach beriladi (tasdiqlanmagan savol bilan
sertifikat chiqmasin).

## 6. PWA va oflayn

Bor: o'rnatish, sahifalar keshi, pleyer (javoblar qurilmada, internet tiklanganda yuboriladi), «Oflayn paket» (10c, 2026-11-26).
AI tutor oflaynda faqat avvalgi javoblarni ko'rsatadi.

**Oflayn paket** — mavzu darslari, rasmlari va oldindan tayyorlangan dars testlari (kalitsiz) bir bosishda yuklanadi:

- Serverda fayl yo'q: odatdagi sahifalar brauzer keshiga (`rm-pack`) yoziladi. 4 darslik mavzu 3 ta testi bilan — 122 KB (o'lchandi).
- Tayyor test — `status = offline` urinish. Savollari band (boshqa testga tushmaydi), lekin «yakunlanmagan» va «berilgan» emas; birinchi
  javob kelganda boshlanadi. Onlayn shu dars testi boshlansa, o'sha test ishlatiladi: savol behuda sarflanmaydi.
- Internetsiz keyingi dars joriy dars testi topshirilgach ochiladi (natijani server keyin baholaydi; 70% dan past bo'lsa, dars odatdagidek
  qayta o'zlashtiriladi).
- Cheklar: paket 30 MB, 10 ta mavzu, 30 kun. Paket o'chirilsa yoki muddati o'tsa, boshlanmagan testlar o'chib, savollari bankka qaytadi.
- Keshdan ochilgan sahifaning himoya tokeni eskirgan bo'lsa, pleyer yangisini olib qayta yuboradi. Chiqishda yuborilmagan javoblar
  bo'lsa ogohlantiriladi.

Tuzatildi: internetsiz ochiladigan sahifa kirish talab qilardi va kirmasdan o'rnatilgan ilovada ochilmasdi; endi ommaviy `/oflayn`.
Mavzu, kunlik va bosqichli testlar paketga kirmaydi (boshlangani keshdan davom etadi).

**Attestatsiya vaqti (qaror, 2026-11-26): vaqt tugagach test yakunlanadi, javob berilgan savollar tekshiriladi, javobsizlari 0 ball.**

- Vaqt serverda: boshqa qurilmada ochilsa ham qolgan vaqt ko'rinadi (ilgari to'liq 120 daqiqa qaytadan boshlanardi).
- «To'xtatish» qoldi, lekin internet bilan: server vaqtni to'xtatadi. Internetsiz to'xtatib bo'lmaydi.
- Fon vazifasi vaqt tugaganidan 1 daqiqa keyin yakunlaydi; u ishlamasa — foydalanuvchi test sahifalarini ochganda.
- Vaqtdan keyin belgilangan javob hisobga olinmaydi (qurilma soati xatosi tuzatiladi). Vaqtida, lekin internetsiz belgilangan javob
  kech kelsa ham qo'shiladi — natija (kalit) ko'rilmagan bo'lsa.

## 7. 6 oy kirilmagan akkaunt

**Tuzatildi (8-bosqich):** `last_seen_at` endi kuniga bir marta yangilanadi (`app/services/activity.py`). Ilgari faqat login
paytida yangilanardi va har kuni kirib yurgan odam ham kirmagandek ko'rinardi.

- Har kecha fon vazifasi: 6 oydan 14 kun oldin ogohlantirish (Telegram yoki email), muddati o'tgach o'chirish.
- Ogohlantirish yuborilmagan akkaunt o'chirilmaydi: yuborilgandan keyin kamida 14 kun beriladi.
- Natija, javob, xato, e'tiroz, konspekt va progress `ON DELETE CASCADE` bilan o'chadi. Umumiy hisoblarda (`ai_usage`, `audit_log`)
  foydalanuvchi bog'lanishi uziladi, IP va shaxsiy matn ham tozalanadi. Zaxira nusxalar 30 kunda almashadi.
- Ekspert va admin akkauntlariga qo'llanmaydi.

**Qaror (2026-11-24): akkaunt o'chadi, sertifikatlari saqlanadi (bajarildi, admin o'chirganda ham).** Sertifikat qatori o'zi yetarli: `user_id` uziladi (`SET NULL`),
ism-familiya, raqam, sana va natija qoladi, `/s/<raqam>` ishlayveradi. Maxfiylik siyosatiga yozildi.

Ixcham saqlash (100 000 sertifikatda o'lchangan, indekslar bilan): 1336 → 124 bayt, 10,8 baravar kam.

| Hozir | Taklif |
|---|---|
| PDF fayl va yo'li | Fayl yo'q: sahifa qatordan chiziladi, brauzer PDF qiladi |
| Raqam matni (20 belgi) | `id` dan hosil qilinadi: INF-yil-000123 |
| `verify_token` 43 belgi va indeks | 8 baytli tasodifiy son; qidiruv `id` bo'yicha |
| Mavzular nomi va foizi har sertifikatda (JSON) | Nomlar bitta umumiy `certificate_layouts` qatorida; sertifikatda foizlar, har mavzuga 1 bayt |
| `issued_at` vaqt bilan | Sana, 4 bayt |

## 8. Himoya (9-bosqich, 2026-11-25)

**Urinishlarni cheklash.** PostgreSQL'da bitta `rate_limits` jadvali (`services/limits.py`), Redis'siz. Ilgari hisob sessiyada
(cookie'da) edi: cookie o'chirilsa yoki eskisi qayta yuborilsa urinishlar qaytadan boshlanardi.

| Nima | Kim bo'yicha | Chegara |
|---|---|---|
| Kirish | akkaunt + IP | 15 daqiqada 5 ta xato |
| Kirish | akkaunt, hamma IP'lardan | 1 soatda 30 ta xato |
| Kirish | IP | 15 daqiqada 100 ta xato |
| Kod so'rash | raqam yoki email | 15 daqiqada 5 ta, kuniga 15 ta |
| Kod so'rash | IP | 1 soatda 200 ta |
| Kodni tekshirish | raqam yoki email | 5 ta xato, keyin yangi kod |
| Maxfiy so'z | akkaunt | 30 daqiqada 5 ta xato, kuniga 15 ta |
| Maxfiy so'z | IP | 30 daqiqada 50 ta xato |
| Joriy parol (profil) | foydalanuvchi | 15 daqiqada 5 ta xato |

- Urinish tekshiruvdan oldin, bitta atomar so'rovda sanaladi: parallel taxminlar chegaradan o'tmaydi. To'g'ri kirish hisobga yozilmaydi.
- IP chegarasi ataylab keng: maktab va mobil operator orqasida yuzlab odam bitta IP bilan chiqadi. IPv6'da /64 bo'yicha.
- Bitta IP akkaunt egasini bloklay olmaydi (4 × 5 < 30); egasi boshqa tarmoqdan kiradi.
- Xotira: 8 baytli HMAC kalit (telefon, email, IP saqlanmaydi), UNLOGGED (WAL yo'q). O'lchandi: indeks bilan qatoriga 80 bayt,
  100 000 qatorda 8 MB; muddati o'tgani o'zi tozalanadi. Kirishga 3 ta qoida uchun 3,8 ms qo'shiladi (parol xeshi ≈ 147 ms).

**Topilgan va tuzatilgan:**

| Topilma | Tuzatish |
|---|---|
| CSRF token 1 soatda eskirardi: 120 daqiqalik attestatsiya testida javoblar serverga yozilmay qolardi | Token sessiya davomida amal qiladi |
| Serverda `123456` kodi bilan istalgan akkauntni egallab olish mumkin edi | Kod faqat ishlab chiqishda; yetkazish ulanmaguncha serverda hech qaysi kod o'tmaydi (`services/codes.py`) |
| `SECRET_KEY` berilmasa ma'lum kalit ishlatilardi | Serverda kalitsiz (yoki 32 belgidan qisqa) ishga tushmaydi |
| `.env` hech qayerda o'qilmasdi | `run.py` o'qiydi (kutubxonasiz) |
| Parol almashganda boshqa qurilmalar kirgan holda qolardi | Sessiya va «eslab qolish» parolga bog'langan (`User.auth_tag`), sessiyalar jadvali kerak emas |
| Tiklash qadami cookie'sini qayta yuborib, parolni yana almashtirish mumkin edi | 15 daqiqa va akkaunt belgisi bilan bir martalik |
| Cookie'larda `Secure` yo'q, HSTS yo'q | Serverda qo'yiladi |
| `MAX_CONTENT_LENGTH` yo'q | 512 KB; dars muharriri 2 MB; fayl yuklash 6 MB. Katta fayl brauzerning o'zida to'xtatiladi |
| Excel'da `ZZZZZZ1` katagi serverni xotirasiz qoldirardi; buzilgan yoki parolli fayl — 500 | Ustunlar 200 tagacha, ochilgan hajm 10 MB, xato matni chiqadi |
| Boshqa saytdagi havola `/chiqish` ni ochib, eslatmalar va yuborilmagan javoblarni o'chirtira olardi | `Sec-Fetch-Site` tekshiriladi |
| Akkaunt bor-yo'qligi javob vaqtidan bilinardi | Topilmaganda ham xesh hisoblanadi |
| Telefon/emailni almashtirishda parolsiz ham «boshqa akkauntga bog'langan» javobi chiqardi | Avval parol tekshiriladi |
| Email'da `'` va `<` qabul qilinardi va Alpine ifodasiga tushardi | Qoida qattiqlashtirildi, qiymat ekranlanadi |
| NUL bayt 500 xato berardi (pleyer cheksiz qayta yuborardi) | Olib tashlanadi yoki 422 |
| Parol tiklanganda egasi bilmasdi | Jurnal va bildirishnoma |
| Ekspert/admin «eslab qolish» 1 yil | 7 kun (o'qituvchida 1 yil) |
| Docker'da baza (paroli ma'lum) butun tarmoqqa ochiq edi | Faqat 127.0.0.1 |
| Kirgan sahifalar umumiy keshga tushishi mumkin edi (Flask 3.0.3, CVE-2026-27205) | `Vary: Cookie`; panel va kirish sahifalari `no-store` |

Kutubxonalar OSV bazasi bilan solishtirildi (31 ta paket): yuqoridagi bitta past darajali zaiflikdan boshqa topilmadi.

**Ataylab qoldirilgan:** ko'p IP'li hujumchi bir akkauntga kirishni 1 soatga yopa oladi (kirgan qurilmalar ishlayveradi, parol
havolasi bilan tiklanadi); ro'yxatdan o'tish va parol tiklash sahifalari raqam band yoki yo'qligini aytadi (qulaylik uchun, IP bo'yicha
cheklangan); chiqilgandan keyin ham o'g'irlangan cookie parol almashguncha ishlaydi (sessiyalar jadvali yo'q).

## 9. Fon vazifalari (10-bosqich, 2026-11-25)

**Navbat** (`services/jobs.py`) — bitta `jobs` jadvali, Redis'siz:

- Vazifa uni qo'ygan tranzaksiya bilan birga yoziladi. `NOTIFY` worker'ni darhol uyg'otadi, bo'sh turganda baza so'ralmaydi.
- Olingan vazifa ijaraga beriladi: worker qulasa, muddat o'tgach boshqasi qaytadan oladi. Parallel worker'lar bir vazifani olmaydi.
- Xatoda 30 s, 2 daq, 8 daq, 32 daq, 2 soatdan keyin qayta; keyin admin panelida to'xtab turadi. Jadvaldagi vazifa to'xtamaydi.
- Ikki yo'lak: tez (kod va xabarlar) va sekin (tungi ishlar, AI) — tungi arxiv tasdiqlash kodini kutdirmaydi.
- Bajarilgan vazifa qatori o'chadi; xato matnida shaxsiy ma'lumot yo'q (`hide_parameters`).

**Worker** (`app/worker.py`) — `RM_WORKER=1` bilan veb-jarayon ichida oqim sifatida. O'lchandi: alohida jarayon 91 MB (shundan 85 MB
Flask, SQLAlchemy va psycopg'ning o'zi), ichkarida +2 MB. Bir nechta gunicorn worker'dan faqat bittasi faol (advisory lock), u
to'xtasa boshqasi 30 soniyada davom ettiradi. Yuklama oshsa, kod o'zgarmasdan `python worker.py` ga o'tiladi.

| Vazifa | Vaqti (Toshkent) | Nima qiladi |
|---|---|---|
| Eski testlarni siqish | har kuni 02:30 | 7 kundan eski yakunlangan testlar arxivga |
| Tozalash | har kuni 03:00 | tugagan cheklovlar, 30 kunlik bildirishnomalar, ishlatilgan taklifnomalar, AI keshi |
| Keraksiz rasmlar | yakshanba 03:30 | hech bir savol, versiya va dars ishlatmaydigan, 7 kundan eski rasmlar (ishlab chiqishda o'chirilmaydi) |
| Savol zaxirasi | har kuni 04:00 | faol o'qituvchilarga yangi savol 2 ta testga yetmayotgan darslar; ekspert panelida ko'rinadi |

Savol zaxirasi o'lchandi: 10 000 o'qituvchi × 303 kichik mavzu (6900 savol) — 1,5 s. Shabloni bor kichik mavzu kirmaydi: unga savol
so'ralganda 8 ms da tuziladi, oldindan tayyorlash faqat joy egallardi. Navbat tezligi: kamida 36 vazifa/s (testlar bilan parallel o'lchandi).

## Manbalar

- Gemini: [hududlar](https://ai.google.dev/gemini-api/docs/available-regions), [narxlar](https://ai.google.dev/gemini-api/docs/pricing),
  [embedding](https://ai.google.dev/gemini-api/docs/embeddings), [shartlar](https://ai.google.dev/gemini-api/terms),
  [o'chirilgan modellar](https://ai.google.dev/gemini-api/docs/deprecations)
- Gemini limitlari (norasmiy): [imisofts](https://imisofts.com/blog/gemini-api-free-tier-limits/)
- [Groq limitlari](https://console.groq.com/docs/rate-limits) · [Cloudflare Workers AI](https://developers.cloudflare.com/workers-ai/platform/pricing/)
- Azure: [tillar](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=tts),
  [narx](https://azure.microsoft.com/en-in/pricing/details/cognitive-services/speech-services)
- [Meta MMS litsenziyasi](https://huggingface.co/facebook/mms-tts-uzb-script_cyrillic) ·
  [halfvec](https://neon.com/blog/dont-use-vector-use-halvec-instead-and-save-50-of-your-storage-cost)
- Shaxsiy ma'lumotlar qonuni: [legal500](https://www.legal500.com/developments/thought-leadership/legislative-updates-in-the-field-of-artificial-intelligence-and-personal-data-regulation-uzbekistan/),
  [49 davlat ro'yxati](https://daryo.uz/ru/2026/08/05/uzbekistan-approves-list-of-49-countries-with-adequate-personal-data-protection/)
