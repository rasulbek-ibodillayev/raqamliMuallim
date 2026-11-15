# raqamliMuallim — foydalanuvchilar bilan sinov rejasi

Maqsad: prototipni 5 nafar haqiqiy informatika o‘qituvchisi bilan sinab, eng muhim qulaylik muammolarini MVP-1 dan oldin topish.

## 1. Tashkiliy qism

| Band | Qiymat |
|---|---|
| Ishtirokchilar | 5 nafar informatika o‘qituvchisi (yoshi 25–35: 2 nafar, 36–50: 2 nafar, 51+: 1 nafar) |
| Qurilma | Har biri o‘z telefonida (Android, o‘rtacha model). Bittasi — kompyuterda |
| Davomiyligi | 30 daqiqa: 5 daqiqa tanishuv, 20 daqiqa vazifalar, 5 daqiqa so‘rovnoma |
| Format | Yuzma-yuz yoki video qo‘ng‘iroq (ekran ulashish bilan) |
| Rollar | Moderator (savol beradi, yordam bermaydi) va kuzatuvchi (yozib boradi) |
| Rozilik | Ekran va ovoz yozilishiga og‘zaki rozilik olinadi; ism hisobotga yozilmaydi (Ishtirokchi 1, 2…) |
| Manzil | Prototip: `http://<server>:5000/` (yoki internetga chiqarilgan sinov manzili) |

## 2. Moderator uchun kirish so‘zi (o‘qib beriladi)

> Biz sizni emas, saytni sinayapmiz — xato qilsangiz, bu saytning kamchiligi. Iltimos, o‘ylayotganlaringizni ovoz chiqarib ayting: nimani qidiryapsiz, nima sizni ajablantirdi. Men savollarga javob bermasligim mumkin, chunki sayt o‘zi tushunarli bo‘lishi kerak. Istalgan payt to‘xtatishingiz mumkin.

## 3. Vazifalar

Har vazifa uchun: muvaffaqiyat mezoni, kutilgan yo‘l va vaqt chegarasi. Vaqt tugasa yoki ishtirokchi «bilmayman» desa — vazifa «bajarilmadi» deb belgilanadi va keyingisiga o‘tiladi.

| № | Vazifa (ishtirokchiga aytiladi) | Muvaffaqiyat mezoni | Kutilgan yo‘l | Vaqt |
|---|---|---|---|---|
| 1 | «Siz saytga birinchi marta kirdingiz. Bilim darajangizni aniqlashni boshlang.» | Diagnostika sahifasida «Diagnostikani boshlash» bosildi | Bosh sahifa → 3 qadamli yo‘riqnoma → «Boshlash» | 2 daq |
| 2 | «Bugun 20 daqiqa vaqtingiz bor. Nima qilishingiz kerakligini toping va boshlang.» | «Keyingi qadam» yoki «Bugun» ro‘yxatidan dars/test ochildi | Bosh sahifa → «Darsni davom ettirish» | 2 daq |
| 3 | «Darsdagi elif haqidagi gapni konspektingizga saqlang, keyin uni konspektda toping.» | Qayd «Shaxsiy konspekt»da ko‘rindi | Matnni belgilash → «Konspektga saqlash» → Menyu → Shaxsiy konspekt | 4 daq |
| 4 | «Testni yeching, bitta savolga javob bermay qoldiring va testni yakunlang.» | Yakunlash oynasida «Javobsiz: 1» ko‘rindi va test yakunlandi | Attestatsiya sinovi → savollar → «Yakunlash» | 5 daq |
| 5 | «Attestatsiyaga ulgurasizmi? Qaysi mavzu eng zaif ekanini ham toping.» | Prognoz sanasini va zaif mavzuni (Funksiyalar yoki xatolar analitikasi) aytdi | Bosh sahifa → Tayyorlik; Bilim darajasi yoki Xatolar analitikasi | 3 daq |

Qo‘shimcha (vaqt qolsa): «Matnni kattaroq qiling» (Profil → Matn o‘lchami yoki darsdagi «Aa»); «Natijangizga e’tiroz bildiring».

## 4. Kuzatuv varag‘i (har ishtirokchi uchun nusxa)

Ishtirokchi: ____  Yosh guruhi: ____  Qurilma: ____  Sana: ____

| № | Bajarildi (ha / yordam bilan / yo‘q) | Vaqt (soniya) | Xatolar soni | Qayerda to‘xtadi / adashdi | Iqtibos (aynan aytgan gapi) |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |
| 5 | | | | | |

Kuzatuvchi uchun belgilar: **?** — ikkilandi; **✗** — noto‘g‘ri joyni bosdi; **↩** — orqaga qaytdi; **!** — ajablandi yoki noroziligini bildirdi.

## 5. Yakuniy so‘rovnoma (SUS, o‘zbekcha)

Har bir fikrga 1 dan 5 gacha baho: 1 — mutlaqo qo‘shilmayman, 5 — to‘liq qo‘shilaman.

1. Bu saytdan muntazam foydalanishni xohlardim.
2. Sayt keraksiz darajada murakkab.
3. Saytdan foydalanish oson edi.
4. Bu saytdan foydalanish uchun texnik yordam kerak bo‘ladi.
5. Saytning turli qismlari bir-biri bilan yaxshi bog‘langan.
6. Saytda nomuvofiqliklar juda ko‘p.
7. Ko‘pchilik bu saytni tez o‘rganib oladi deb o‘ylayman.
8. Saytdan foydalanish noqulay edi.
9. Saytdan foydalanishda o‘zimni ishonchli his qildim.
10. Saytdan foydalanishdan oldin ko‘p narsani o‘rganishim kerak edi.

**Hisoblash:** toq savollar: (baho − 1); juft savollar: (5 − baho). Yig‘indi × 2.5 = SUS ball (0–100). 68 dan yuqori — o‘rtachadan yaxshi; maqsad: **≥ 75**.

Ochiq savollar:
- Saytda sizga eng yoqqan narsa nima bo‘ldi?
- Qayerda eng ko‘p qiynaldingiz?
- Bitta narsani o‘zgartira olsangiz, nimani o‘zgartirardingiz?

## 6. Natijalarni tahlil qilish

1. Har vazifa bo‘yicha: bajarilish foizi, o‘rtacha vaqt, xatolar soni.
2. Muammolarni jadvalga yig‘ish va jiddiyligini baholash:

| Daraja | Ta’rif | Misol |
|---|---|---|
| Kritik | Vazifani bajarib bo‘lmaydi | Yakunlash tugmasi topilmadi |
| Jiddiy | Bajariladi, lekin katta qiyinchilik bilan | Konspektni topish uchun 3 ta sahifa ochildi |
| Kichik | Biroz noqulaylik | Matn mayda ko‘rindi |

3. Bir xil muammo 2 va undan ortiq ishtirokchida takrorlansa — birinchi navbatda tuzatiladi.
4. Hisobot: 1 sahifa — 5 ta asosiy muammo, har biriga skrinshot va taklif qilingan yechim.

## 7. Analitikada kuzatiladigan hodisalar (backend bilan birga)

TZ 1.3-bo‘limdagi ko‘rsatkichlarni o‘lchash uchun quyidagi hodisalar yoziladi:

| Hodisa | Qachon | Qaysi ko‘rsatkich uchun |
|---|---|---|
| `onboarding_step_done` | Yo‘riqnoma qadami bajarilganda | Diagnostikani yakunlaganlar ≥ 60% |
| `diagnostic_finished` | Diagnostika yakunlanganda | ″ |
| `session_start` | Har kirishda | 7 kundan keyin qaytganlar ≥ 35% |
| `topic_passed` | Mavzu testidan o‘tilganda | Rejaning ≥ 50% ini o‘tganlar ≥ 25% |
| `search_used`, `note_saved`, `selection_menu_used` | Yangi funksiyalar ishlatilganda | Funksiyalar foydaliligini baholash |
| `font_size_changed` | Matn o‘lchami o‘zgarganda | Accessibility ehtiyojini baholash |
