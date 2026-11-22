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
| user_topic_progress | Mavzu holati, belgilar, dars progressi, ketma-ket muvaffaqiyatsizliklar |
| error_items | Xatolar analitikasi va xatolar ro'yxati (kichik mavzu darajasida) |
| review_schedule | Takrorlash jadvali (spaced repetition) |
| method_stats | Tushuntirish usullari samaradorligi (10.3-bo'lim) |
| objections, discussions | E'tirozlar, muhokama xabarlari, ekspert qarorlari |
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
  (`expert`/`ai`), holat (`draft`, `review`, `approved`, `paused`, `archived`), versiya.
  6.1 kelgach moslashtiriladi.
- **Versiyalar.** `questions` joriy holatni saqlaydi, har tahrir `question_versions`ga to'liq
  nusxa (JSONB) sifatida yoziladi. `attempt_items` va `objections` savolning aniq versiyasiga ishora qiladi.
- **attempt_items ixcham.** Alohida `id` yo'q: kalit `(attempt_id, position)`.
  Arxivlangan urinishda tafsilotlar `test_attempts.items_archive`ga (zlib + JSON) siqiladi.
- **Oflayn sinxronlash.** `test_attempts.client_uuid`: IndexedDB'dan qayta yuborilgan javoblar ikki marta yozilmaydi.
- **Attestatsiya sanasi** `users.exam_date`da, uni admin kiritadi.
- **Vektor o'lchami** 768 (Gemini `text-embedding-004`), `app/models/rag.py`dagi `EMBED_DIM`.
- **Holat/tur maydonlari** Postgres ENUM emas, `String` + `CHECK` cheklovi: qiymat qo'shish oddiy migratsiya bilan bo'ladi.
