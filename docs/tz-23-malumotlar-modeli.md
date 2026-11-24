# TZ 23. Ma'lumotlar modeli (asosiy jadvallar)

> Texnik topshiriqdan ko'chirma (16-noyabr, 2026). Kod: `app/models/`, migratsiyalar: `migrations/`.

| Jadval | Mazmuni |
|---|---|
| users | Telefon/email, parol xeshi, ism, familiya, rol, ixtiyoriy viloyat/tuman, Telegram ID, rozilik sanasi |
| courses, sections, topics, subtopics | Kontent ierarxiyasi; subtopics'da og'irlik (testdagi savollar soni) |
| topic_prerequisites | Mavzular bog'liqliklari |
| content_blocks | Dars bloklari (turi, ma'lumot JSONB, ovozli matn, versiya, xesh) |
| questions | 6.1-bo'limdagi maydonlar, versiyalar bilan |
| test_attempts | Har bir boshlangan test: turi, holati, bosqich, natija, qaror, boshlangan paytdagi sozlamalar nusxasi |
| attempt_items | Har bir berilgan savol: javob, ball, vaqt (ixcham) |
| user_seen | Foydalanuvchiga berilgan savollar bitmapi (bir savol ikki marta berilmasligi uchun) |
| user_topic_progress | Mavzu holati, belgilar, dars progressi, ketma-ket muvaffaqiyatsizliklar |
| error_items | Xatolar analitikasi va xatolar ro'yxati (kichik mavzu darajasida) |
| review_schedule | Takrorlash jadvali (spaced repetition) |
| method_stats | Tushuntirish usullari samaradorligi (10.3-bo'lim) |
| objections, discussions | E'tirozlar, muhokama xabarlari, ekspert qarorlari |
| notifications | Bildirishnomalar: turi, havola, eski va yangi foiz (matnsiz, 30 kun) |
| expert_profiles | Ekspert huquqlari va mavzulari |
| notes | Shaxsiy konspekt |
| certificates | Sertifikatlar va tekshiruv tokenlari |
| ai_cache, ai_usage | AI javoblari keshi va sarf hisobi |
| audio_assets | Keshlangan audio fayllar |
| rag_sources, rag_chunks | RAG manbalari va vektorlar |
| settings, audit_log | Barcha chegaralar va sozlamalar; admin harakatlari jurnali |

**Taklif. Xotirani tejash usullari:** test natijalari ixcham jadvalda (savol ID, javob, ball, vaqt);
AI darslari va audio har foydalanuvchi uchun emas, har mavzu uchun bir marta saqlanadi;
sxemalar rasm emas, matnli Mermaid kod sifatida saqlanadi; 1 yildan eski urinishlarning
tafsilotlari arxivga siqib o'tkaziladi, umumiy natijalari qoladi.

## Amalga oshirishdagi qarorlar

- **questions (6.1-bo'lim hali qo'lda yo'q).** Maydonlar ekranlar asosida tuzildi: tur
  (`single`, `multiple`, `open`, `matching`), qiyinlik (`easy`, `medium`, `hard` = 1–3-bosqich),
  matn, `data` JSONB (variantlar, kod, rasm, jadval, juftliklar), `answer` JSONB, izoh, manba
  (`expert`/`import`/`ai`/`template`), holat (`draft`, `review`, `approved`, `paused`, `archived`), versiya.
  6.1 kelgach moslashtiriladi.
- **Versiyalar.** `questions` joriy holatni saqlaydi, har tahrir `question_versions`ga to'liq
  nusxa (JSONB) sifatida yoziladi. `attempt_items` va `objections` savolning aniq versiyasiga ishora qiladi.
- **attempt_items ixcham.** Bu eng katta jadval bo'ladi, shuning uchun:
  - alohida `id` yo'q: kalit `(attempt_id, position)`;
  - savol matni nusxalanmaydi, faqat `(question_id, question_version)` havolasi saqlanadi;
  - ustunlar tekislash tartibida joylashgan (`bigint`, `int`, `int`, `int`, `smallint`, `smallint`, `jsonb`),
    shuning uchun qatorda bo'sh to'ldiruvchi bayt yo'q;
  - ball `smallint` turida, 0–100 foiz (`float8` o'rniga);
  - `question_id` bo'yicha alohida indeks yo'q.

  Test (bosqich) tugagach javobda faqat `v` qoladi. 12 oydan eski urinish qatorlari `test_attempts.items_archive`ga
  (zlib + JSON) siqiladi: `flask eski-testlarni-siqish`. Natija sahifasi, e'tiroz va foizlar arxivdan ham o'qiydi
  (`app/services/archive.py`, `rows`). Bekor qilingan test qatorlari darhol o'chadi.
- **Savol identifikatorlari 4 baytli.** `questions.id` va unga havola qiluvchi barcha ustunlar `integer`
  (`question_versions`, `attempt_items`, `objections`, `discussions`, `error_items`).
  Savollar 2 milliarddan oshmaydi.
- **Bir savol bir foydalanuvchiga ikki marta berilmaydi.** Bu qoida `user_seen (user_id, bits)` ga tayanadi: bitmapda
  n-bit — `questions.id = n` savol berilgan (`app/services/seen.py`). `attempt_items` arxivlanganda ham qoladi.
  - Testlar `app/services/attempts.py` orqali yig'iladi: kichik mavzular `weight`i bo'yicha, faqat `approved` savollardan.
  - Har bir kichik mavzuda berilmagan savollar tasodifiy tartibda olinadi. Yakunlanmagan bosqichli testning keyingi
    bosqichlaridagi savollar band: boshqa testga tushmaydi.
  - Yetmasa shablon generator (`app/services/generator.py`, `subtopics.generators`) yangi savol tuzadi. Javob kod bilan
    hisoblanadi, savol `source=template`, `approved` bo'lib bankka qo'shiladi; `questions.sig` takrorni oldini oladi.
  - U ham yetmasa test qisqaroq bo'ladi, umuman qolmasa test ochilmaydi va sabab ko'rsatiladi.
- **Natijani qayta hisoblash** (`app/services/recalc.py`). E'tiroz qabul qilinsa yoki AI savoli rad etilsa: ball va foiz faqat
  oshadi. Kalit o'zgarsa — variantlari bir xil versiyalardagi javoblar qayta baholanadi va yangi versiyaga o'tadi. Savol hisobdan
  chiqarilsa — `attempt_items.score` NULL, tartibi `settings_snapshot.dropped` da, foiz qolganlaridan. Bosqichli testda endi o'tgan
  mavzuning berilmagan yuqori bosqich savollari ham chiqariladi. Arxivlangan va yakunlanmagan testlar ham qamrab olinadi.
- **Bildirishnomalar.** Qatorda matn yo'q (`kind`, `ref_id`, foizlar). O'qilganlik — `users.notif_seen_at`. 30 kundan eskisi
  ko'rsatilmaydi va shu foydalanuvchiga keyingisi yozilganda o'chadi.
- **Darsni saqlash.** Dars butunlay bitta so'rovda saqlanadi; `rev` (qatorlar id'si va `updated_at` izi) mos kelmasa — 409, hech narsa
  yozilmaydi. Savoli bor mavzu, dars va kichik mavzu o'chmaydi — dars nashrdan olinadi.
- **Xato tuzatilishi.** Savol qaytmagani uchun xato shu kichik mavzudagi boshqa savolga keyingi testdagi to'liq to'g'ri
  javob bilan yopiladi: bitta to'g'ri javob — bitta, eng eski xato. «Qayta xato» — shu kichik mavzuda nechta testda xato
  qilingani.
- **Test turlari.** `test_attempts.kind`: diagnostic, lesson, topic, daily, interim, weekly, monthly, optional, final, errors,
  exam. Dars testi `subtopic_id` ga bog'lanadi. Bosqichli testda `stage` — joriy bosqich, bosqichlar chegarasi va o'tmagan
  mavzular `settings_snapshot` da (`stages`, `failed_topics`, `skipped`).
- **Vaqt.** `deadline_at` ma'lumot uchun: mashq testlarini to'xtatib turish mumkin, shuning uchun server kech kelgan javobni
  rad etmaydi; vaqtni pleyer hisoblaydi va tugaganda testni o'zi yakunlaydi.
- **Oflayn sinxronlash.** `test_attempts.client_uuid`: IndexedDB'dan qayta yuborilgan javoblar ikki marta yozilmaydi.
- **Attestatsiya sanasi** `users.exam_date`da, uni admin kiritadi.
- **Vektor o'lchami** 768, `app/models/ai.py`dagi `EMBED_DIM`. `text-embedding-004` 2026-01-14 da o'chirilgan: 13-bosqichda `gemini-embedding-2` va `halfvec`ga o'tadi.
- **Holat/tur maydonlari** Postgres ENUM emas, `String` + `CHECK` cheklovi: qiymat qo'shish oddiy migratsiya bilan bo'ladi.
