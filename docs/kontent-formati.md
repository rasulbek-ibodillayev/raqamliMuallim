# Kontent formati (JSON)

Mavzular, dars bloklari va savollar bitta JSON faylda tayyorlanadi va bazaga quyidagi buyruq bilan yuklanadi:

```bash
FLASK_APP=run.py .venv/Scripts/flask kontent-yuklash savollar.json
```

- Yangi savollar `review` holatida tushadi va ekspert ularni tasdiqlaydi. Darhol tasdiqlangan holda yuklash uchun `--holat approved`.
- Avval butun fayl tekshiriladi. Bitta xato bo'lsa ham bazaga hech narsa yozilmaydi. Xatolar joyi bilan chiqadi, masalan: `sections[0].topics[1].subtopics[0].questions[2]: answer.keys: 0..3 oralig'idagi takrorlanmas indekslar`.
- Faylni qayta yuklash xavfsiz, hech narsa takrorlanmaydi:
  - bo'lim, mavzu va kichik mavzular nomi bo'yicha topilib yangilanadi;
  - bazada bor savol o'tkazib yuboriladi va o'zgartirilmaydi. Mavjud savolni ekspert panelida tahrirlang.
- Namuna: [app/seed/namuna_kontent.json](../app/seed/namuna_kontent.json). Fayl nomisiz buyruq aynan shu namunani yuklaydi.

## Tuzilishi

```json
{
  "course": {"slug": "informatika", "title": "Informatika"},
  "sections": [
    {"title": "Dasturlash", "topics": [
      {"title": "Python: shart operatorlari", "est_minutes": 12, "subtopics": [
        {"title": "if operatori", "weight": 2, "blocks": [ ... ], "questions": [ ... ]}
      ]}
    ]}
  ]
}
```

Tartib JSON'dagi tartib bilan bir xil bo'ladi.

**`weight`**: mavzu testida shu kichik mavzudan nechta savol beriladi. 0 dan 50 gacha. Agar 0 bo'lsa, kichik mavzudan savol olinmaydi.

## Savollar

| Maydon | Majburiy | Qiymat |
|---|---|---|
| `type` | ha | `single`, `multiple`, `open`, `matching` |
| `difficulty` | ha | `easy`, `medium`, `hard` (1–3-bosqich) |
| `text` | ha | Savol matni |
| `data` | turiga qarab | Variantlar, kod, jadval, rasm |
| `answer` | ha | To'g'ri javob (pastda) |
| `explanation` | yo'q | Natijada ko'rsatiladigan izoh |
| `time_limit_s` | yo'q | Savolga ajratilgan vaqt, soniyalarda |
| `source` | yo'q | `import` (standart) yoki `ai`. AI tuzgan savol har doim `review` holatida tushadi va ekspertning «Tekshiruv navbati»ga chiqadi |

Variant indekslari 0 dan boshlanadi.

**Bitta javobli (`single`):**

```json
{"type": "single", "difficulty": "easy", "text": "DNS serverning vazifasi?",
 "data": {"options": ["Fayl uzatish", "Domen nomini IP-manzilga o‘girish", "Xat yuborish"]},
 "answer": {"keys": [1]}}
```

**Ko'p javobli (`multiple`):** `answer.keys` da bir nechta indeks bo'ladi, masalan `[0, 2, 4]`.

**Ochiq javob (`open`):**

```json
{"type": "open", "difficulty": "medium", "text": "101101₂ ni o‘nlikka o‘tkazing.",
 "answer": {"value": "45", "accept": ["45₁₀"]}}
```

`accept` maydoni ixtiyoriy: unda to'g'ri deb qabul qilinadigan boshqa yozilishlar beriladi.

**Moslashtirish (`matching`):** `pairs[k]` — chap ustundagi `k`-element o'ng ustundagi qaysi elementga mos kelishi.

```json
{"type": "matching", "difficulty": "easy", "text": "Moslang.",
 "data": {"left": ["HTTP", "DNS"], "right": ["Domen nomini o‘giradi", "Gipermatn uzatadi"]},
 "answer": {"pairs": [1, 0]}}
```

Bu misolda HTTP «Gipermatn uzatadi» ga, DNS esa «Domen nomini o‘giradi» ga mos keladi.

**Qo'shimcha `data` maydonlari** (har qanday turga qo'shiladi):
- `"code": "x = 5\nprint(x)"` — kod bo'lagi;
- `"table": {"head": [...], "rows": [[...], ...]}` — jadval;
- `"image": {"src": "img/fayl.svg", "alt": "Rasm tavsifi", "caption": "1-rasm"}` — rasm. Rasm uchun SVG yoki WebP, `alt` majburiy.

## Dars bloklari

```json
{"kind": "text", "data": {"title": "if operatori", "body": "..."}, "audio_text": "Ovozli o‘qish uchun matn"}
```

`kind` qiymatlari: `text`, `code`, `image`, `table`, `mermaid` (`data.code` — sxema matni), `formula`, `video`, `callout`, `example`, `quiz`. `example` (yechimli masala) bazaga yuklanadi, lekin darsda ko'rsatilmaydi.
