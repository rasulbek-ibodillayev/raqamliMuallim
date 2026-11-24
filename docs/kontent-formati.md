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

**`generators`** (ixtiyoriy): foydalanuvchiga yangi savol qolmaganda ishlatiladigan shablonlar, masalan `["bin_dec", "bin_match"]`.
Shablon sonlarni har safar yangidan tanlaydi, javobni kod hisoblaydi, savol darhol tasdiqlangan bo'lib bankka qo'shiladi.
Dars testi uchun kamida bitta ko'p javobli yoki moslashtirish shablonini qo'shing. Maydon berilmasa, avvalgisi o'zgarmaydi.
Kichik mavzuda kamida bitta oddiy tasdiqlangan savol ham bo'lishi kerak. Shablonlar ro'yxati — [pastda](#shablonlar).

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

**Variant izohlari** (ixtiyoriy, `single` va `multiple`): `answer.notes` — har bir variant nega to'g'ri yoki noto'g'ri ekani, variantlar
tartibida. Testdan keyin «Yechimini ko'rish» bosilganda AI tutorda chiqadi. Nazariy savollarga yozish tavsiya etiladi:

```json
"answer": {"keys": [1], "notes": ["Fayl uzatish — FTP vazifasi.", "DNS nomni IP-manzilga o‘giradi.", "Xatni SMTP uzatadi."]}
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

`kind` qiymatlari: `text`, `code`, `image`, `table`, `mermaid` (`data.code` — sxema matni), `formula`, `video`, `callout`, `links` (`data.links`: `[{"title", "url"}]`, faqat https), `example`, `quiz`. `example` (yechimli masala) bazaga yuklanadi, lekin darsda ko'rsatilmaydi.

## Shablonlar

`generators` uchun nomlar (`app/services/question_templates.py`):

| Nomi | Mazmuni | Turi | Darajalar |
|---|---|---|---|
| `bin_dec` | Ikkilikdan o‘nlikka | bitta javobli | oson, o'rta, qiyin |
| `bin_dec_open` | Ikkilikdan o‘nlikka (ochiq) | ochiq | oson, o'rta, qiyin |
| `dec_bin` | O‘nlikdan ikkilikka | bitta javobli | oson, o'rta, qiyin |
| `bin_add` | Ikkilik sonlarni qo‘shish | bitta javobli | oson, o'rta, qiyin |
| `bin_match` | Ikkilik va o‘nlik sonlarni moslash | moslashtirish | oson, o'rta, qiyin |
| `hex_dec` | O‘n oltilikdan o‘nlikka | bitta javobli | oson, o'rta, qiyin |
| `hex_dec_open` | O‘n oltilikdan o‘nlikka (ochiq) | ochiq | oson, o'rta, qiyin |
| `dec_hex` | O‘nlikdan o‘n oltilikka | bitta javobli | oson, o'rta, qiyin |
| `hex_bin` | O‘n oltilikdan ikkilikka | bitta javobli | o'rta, qiyin |
| `hex_match` | O‘n oltilik va o‘nlik sonlarni moslash | moslashtirish | oson, o'rta, qiyin |
| `bits_alphabet` | Alifbo quvvati | bitta javobli | oson, o'rta |
| `text_volume` | Matn hajmi | bitta javobli | o'rta, qiyin |
| `unit_convert` | Axborot birliklarini o‘tkazish (ochiq) | ochiq | oson, o'rta, qiyin |
| `unit_match` | Axborot birliklarini moslash | moslashtirish | oson, o'rta |
| `logic_count` | Mantiqiy ifoda necha holatda rost | bitta javobli | o'rta, qiyin |
| `logic_true` | Rost mantiqiy ifodalar | ko'p javobli | oson, o'rta, qiyin |
| `logic_value` | Mantiqiy ifoda qiymatlari | moslashtirish | o'rta, qiyin |
| `de_morgan` | De Morgan qonunlari | bitta javobli | oson, o'rta |
| `py_if` | if operatori: natija | bitta javobli | oson, o'rta, qiyin |
| `py_if_open` | if operatori: natija (ochiq) | ochiq | oson, o'rta, qiyin |
| `py_true` | Rost shartlar | ko'p javobli | oson, o'rta, qiyin |
| `py_ifelse` | if / else: natija | bitta javobli | oson, o'rta, qiyin |
| `py_ifelse_match` | if / else: qiymatlarni moslash | moslashtirish | oson, o'rta, qiyin |
| `py_elif` | elif zanjiri: natija | bitta javobli | oson, o'rta, qiyin |
| `py_elif_match` | elif zanjiri: baholarni moslash | moslashtirish | oson, o'rta, qiyin |
| `py_for` | for sikli: yig‘indi | bitta javobli | oson, o'rta, qiyin |
| `py_for_count` | for sikli: shartli hisob (ochiq) | ochiq | o'rta, qiyin |
| `py_range` | range() elementlari | ko'p javobli | oson, o'rta, qiyin |
| `py_while` | while sikli: natija | bitta javobli | oson, o'rta, qiyin |
| `py_rec` | Rekursiya: natija | bitta javobli | oson, o'rta, qiyin |
| `py_rec_match` | Rekursiya: qiymatlarni moslash | moslashtirish | o'rta, qiyin |
| `bsearch_steps` | Ikkilik qidiruv qadamlari | bitta javobli | oson, o'rta, qiyin |
| `bsearch_mid` | Ikkilik qidiruv: birinchi solishtirish | bitta javobli | oson, o'rta, qiyin |
| `search_true` | Qidiruv haqida to‘g‘ri fikrlar | ko'p javobli | oson, o'rta, qiyin |
| `xl_sumif` | SUMIF formulasi | bitta javobli | oson, o'rta, qiyin |
| `xl_countif` | COUNTIF formulasi | bitta javobli | oson, o'rta, qiyin |
| `xl_match` | Formulalarni natijasi bilan moslash | moslashtirish | oson, o'rta, qiyin |
