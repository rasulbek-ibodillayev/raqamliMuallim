"""Interfeys asosiy qismining qoraqalpoqcha (lotin yozuvi) tarjimasi.

scripts/translate.py shu lug'atni kaa/LC_MESSAGES/messages.po ga yozadi; qolgan satrlarni tarjima xizmati
(RM_TRANSLATE_URL) bilan to'ldiradi. Chiqarishdan oldin qoraqalpoq tili mutaxassisi ko'rib chiqishi tavsiya etiladi.
"""

KAA = {
    # Menyu va qobiq
    "Bosh sahifa": "Bas bet", "O‘quv reja": "Oqıw rejesi", "Natijalarim": "Nátiyjelerim", "O‘qish": "Oqıw",
    "AI tutor": "AI tutor", "Eslatmalar": "Eslatpalar", "Muhokamalar": "Talqılawlar", "Test va natijalar": "Test hám nátiyjeler",
    "Testlar": "Testler", "Xatolar analitikasi": "Qátelikler analitikası", "E’tirozlarim": "Ápellyaciyalarım",
    "Sertifikatlarim": "Sertifikatlarım", "Reja": "Reje", "Yana": "Jáne", "Profil": "Profil", "Yordam": "Járdem",
    "Chiqish": "Shığıw", "Asosiy menyu": "Tiykarǵı menyu", "Menyuni ochish": "Menyunı ashıw", "Menyuni yopish": "Menyunı jabıw",
    "Bildirishnomalar": "Xabarlandırıwlar", "Qidirish (Ctrl+K)": "Izlew (Ctrl+K)", "Mavzu rangini almashtirish": "Reńdi ózgertiw",
    "Pastki menyu": "Tómengi menyu", "Interfeys tili": "Interfeys tili", "Asosiy kontentga o‘tish": "Tiykarǵı mazmunǵa ótiw",
    "raqamliMuallim": "raqamliMuallim", "Attestatsiyagacha": "Attestaciyaǵa shekem", "kun": "kún",
    "Hech narsa topilmadi.": "Hesh nárse tabılmadı.", "Qidiruv": "Izlew",
    "Ekspert paneli": "Ekspert paneli", "Admin paneli": "Admin paneli", "Savollar banki": "Sorawlar bankı",
    "Mavzular va darslar": "Temalar hám sabaqlar", "E’tirozlar": "Ápellyaciyalar", "Statistika": "Statistika",
    "Foydalanuvchilar": "Paydalanıwshılar", "Ekspertlar": "Ekspertler", "Sozlamalar": "Sazlawlar",

    # Umumiy tugmalar
    "Saqlash": "Saqlaw", "Bekor qilish": "Biykarlaw", "Tasdiqlash": "Tastıyıqlaw", "Yopish": "Jabıw", "Orqaga": "Artqa",
    "O‘chirish": "Óshiriw", "Tahrirlash": "Redaktorlaw", "Ko‘rish": "Kóriw", "Boshlash": "Baslaw", "Davom ettirish": "Dawam ettiriw",
    "Keyingisi": "Keyingisi", "To‘xtatish": "Toqtatıw", "Yuborish": "Jiberiw", "Kod yuborish": "Kod jiberiw",
    "Qayta yuborish": "Qayta jiberiw", "Ko‘rsatish": "Kórsetiw", "Yashirish": "Jasırıw", "Tanlang": "Tańlań",
    "Hammasi": "Barlıǵı", "Keyinroq": "Keyinirek",

    # Kirish va ro'yxatdan o'tish
    "Kirish": "Kiriw", "Parol": "Parol", "Parolni takrorlang": "Paroldi qaytalań", "Parolni tiklash": "Paroldi tiklew",
    "Yangi parol": "Jańa parol", "Joriy parol": "Házirgi parol", "Parolni saqlash": "Paroldi saqlaw",
    "Ism": "Atı", "Familiya": "Familiyası", "Oxirgi qadam": "Aqırǵı qádem", "Ro‘yxatdan o‘tish": "Dizimnen ótiw",
    "Maxfiy so‘z": "Jasırın sóz", "Boshqa usul": "Basqa usıl", "Tasdiqlash kodi": "Tastıyıqlaw kodı",
    "Telefon raqam yoki email": "Telefon nomeri yamasa email", "Email manzil": "Email mánzili",
    "Email orqali tasdiqlash": "Email arqalı tastıyıqlaw", "Raqamni tasdiqlang": "Nomerdi tastıyıqlań",
    "Telegram botni ochish": "Telegram bottı ashıw", "Telegram botni oching": "Telegram bottı ashıń",
    "Kodni qayta yuborish": "Kodtı qayta jiberiw", "Kod amal qiladi:": "Kod ámel etedi:", "Kod tasdiqlandi": "Kod tastıyıqlandı",
    "Ismingiz sertifikatda shunday yoziladi.": "Atıńız sertifikatta usılay jazıladı.",
    "Kamida 8 ta belgi, harf va raqam": "Keminde 8 belgi, hárip hám san",
    "Bu raqam orqali ro‘yxatdan o‘tilmagan. Raqamni tekshiring yoki email orqali tiklang":
        "Bul nomer arqalı dizimnen ótilmegen. Nomerdi tekseriń yamasa email arqalı tikleń",
    "Kodning amal qilish muddati (5 daqiqa) tugadi. Yangi kod so‘rang.": "Kodtıń ámel etiw múddeti (5 minut) tawsıldı. Jańa kod sorań.",

    # Sertifikat
    "Sertifikatni tekshirish": "Sertifikattı tekseriw", "Sertifikat haqiqiy.": "Sertifikat haqıyqıy.",
    "Sertifikat muddati o‘tgan.": "Sertifikattıń múddeti ótken.", "05.01.2026 dan boshlab amal qilmaydi.": "05.01.2026 dan baslap ámel etpeydi.",
    "Sabab:": "Sebebi:", "sertifikat berilgan kundan boshlab 3 yil amal qiladi (berilgan sana: 05.01.2023).":
        "sertifikat berilgen kúnnen baslap 3 jıl ámel etedi (berilgen sánesi: 05.01.2023).",

    # Bosh sahifa
    "Salom,": "Sálem,", "Attestatsiya": "Attestaciya", "kun qoldi": "kún qaldı", "Darsni davom ettirish": "Sabaqtı dawam ettiriw",
    "Keyingi mavzu": "Keyingi tema", "Majburiy nazorat testini boshlash": "Májbúriy qadaǵalaw testin baslaw",
    "Attestatsiyaga tayyorlik": "Attestaciyaǵa tayarlıq", "Xato qilayotgan mavzularingiz": "Qátelik jiberip atırǵan temalarıńız",
    "Oldingi testlaringiz bo‘yicha xatolik foizi": "Aldıńǵı testlerińiz boyınsha qátelik procenti", "daqiqa": "minut", "daq": "min",
    "Bugun kichik qadam — ertaga katta natija.": "Búgin kishi qádem — erteń úlken nátiyje.",
    "Har bir to‘g‘ri javob sizni maqsadga yaqinlashtiradi.": "Hár bir durıs juwap sizdi maqsetke jaqınlastıradı.",
    "Bilim — eng ishonchli sarmoya.": "Bilim — eń isenimli investiciya.",
    "Xato qilish — o‘rganishning bir qismi.": "Qátelesiw — úyreniwdiń bir bólegi.",
    "Izchillik iqtidordan kuchliroq.": "Izbe-izlik talanttan kúshlirek.",
    "Bugun o‘rgangan narsangiz ertangi darsingizni boyitadi.": "Búgin úyrengen nárseńiz ertengi sabaǵıńızdı bayıtadı.",
    "Oz-ozdan, lekin har kuni.": "Az-azdan, biraq hár kúni.",
    "Siz uddalaysiz — attestatsiya yaqin!": "Siz uddalaysız — attestaciya jaqın!",

    # O'quv reja
    "O‘zlashtirish holati": "Ózlestiriw jaǵdayı", "Hozirgi mavzu": "Házirgi tema", "Qayta o‘zlashtirish": "Qayta ózlestiriw",
    "Qayta o‘zlashtirish tavsiya etiladi": "Qayta ózlestiriw usınıladı", "Majburiy": "Májbúriy", "Ixtiyoriy": "Iqtıyarıy",
    "O‘zlashtirilmagan": "Ózlestirilmegen", "O‘rganilmoqda": "Úyrenilmekte", "Qayta o‘zlashtirish kerak": "Qayta ózlestiriw kerek",
    "O‘zlashtirilgan": "Ózlestirilgen", "Mustahkam": "Bekkem",

    # Testlar va natijalar
    "Testni boshlash": "Testti baslaw", "Attestatsiya testi": "Attestaciya testi", "Haftalik test": "Háptelik test",
    "Ixtiyoriy test": "Iqtıyarıy test", "Test turlari haqida": "Test túrleri haqqında", "Savollar va javoblar": "Sorawlar hám juwaplar",
    "Testni qayta topshirish": "Testti qayta tapsırıw", "Qayta topshirish": "Qayta tapsırıw", "Sizning javobingiz": "Sizdiń juwabıńız",
    "To‘g‘ri javob": "Durıs juwap", "To‘g‘ri": "Durıs", "Xato": "Qáte", "Javobsiz": "Juwapsız",
    "Xatolar ustida ishlash": "Qátelikler ústinde islew", "Xatolaringizga o‘xshash testlar bajarish": "Qátelikleriñizge uqsas testler orınlaw",
    "Testga o‘tish": "Testke ótiw", "Nechta test ishlaysiz?": "Neshe test isleysiz?",
    "Mavzular bo‘yicha o‘zlashtirish": "Temalar boyınsha ózlestiriw", "Tavsiya": "Usınıs",
    "E’tirozni o‘chirish": "Ápellyaciyanı óshiriw", "E’tiroz o‘chirildi": "Ápellyaciya óshirildi",

    # Dam olish
    "Ko‘zlaringizga dam bering": "Kózleriñizge dem beriń", "5 daqiqa dam olish": "5 minut dem alıw",
    "Tanaffus": "Tánepis", "Majburiy tanaffus": "Májbúriy tánepis",
    "Siz tizimdan 45 daqiqa foydalandingiz. Endi 5 daqiqa davomida ko‘zlaringizga dam bering: kamida 20 soniya davomida taxminan 6 metr uzoqlikdagi narsaga qarang. Bu ko‘z mushaklarini bo‘shashtiradi va ko‘z charchashi, qurishi hamda bosh og‘rig‘ining oldini oladi.":
        "Siz sistemadan 45 minut paydalandıńız. Endi 5 minut dawamında kózleriñizge dem beriń: keminde 20 sekund dawamında shama menen 6 metr uzaqlıqtaǵı nársege qarań. Bul kóz bulshıq etlerin bosańlatadı hám kózdiń sharshawı, qurǵawı hám bas awırıwınıń aldın aladı.",

    # Ekspert
    "Tekshiruv navbati": "Tekseriw gezegi", "Savol yaratish": "Soraw jaratıw", "Savol qo‘shish": "Soraw qosıw",
    "Rad etish": "Biykarlaw", "Mavzu yaratish": "Tema jaratıw", "Dars qo‘shish": "Sabaq qosıw", "Havola biriktirish": "Siltewme biriktiriw",
    "Mavzu": "Tema", "Dars": "Sabaq", "Qiyinlik darajasi": "Qıyınlıq dárejesi", "Savol turi": "Soraw túri", "Savol formati": "Soraw formatı",
    "Savol matni": "Soraw teksti", "Oson": "Ańsat", "O‘rta": "Orta", "Qiyin": "Qıyın",
}
