"""Interfeys asosiy qismining inglizcha tarjimasi (menyu, kirish, tugmalar, yangi bo'limlar).

scripts/translate.py shu lug'atni en/LC_MESSAGES/messages.po ga yozadi; qolgan satrlarni tarjima xizmati
(RM_TRANSLATE_URL) bilan avtomatik to'ldiradi. Tarjima bo'lmagan satr o'zbekcha ko'rinadi.
"""

EN = {
    # Menyu va qobiq
    "Bosh sahifa": "Home", "O‘quv reja": "Study plan", "Natijalarim": "My results", "O‘qish": "Learning",
    "AI tutor": "AI tutor", "Eslatmalar": "Notes", "Muhokamalar": "Discussions", "Test va natijalar": "Tests and results",
    "Testlar": "Tests", "Xatolar analitikasi": "Error analytics", "E’tirozlarim": "My appeals", "Sertifikatlarim": "My certificates",
    "Reja": "Plan", "Yana": "More", "Profil": "Profile", "Yordam": "Help", "Chiqish": "Log out", "Asosiy menyu": "Main menu",
    "Menyuni ochish": "Open menu", "Menyuni yopish": "Close menu", "Bildirishnomalar": "Notifications",
    "Qidirish (Ctrl+K)": "Search (Ctrl+K)", "Mavzu rangini almashtirish": "Toggle theme", "Pastki menyu": "Bottom menu",
    "Interfeys tili": "Interface language", "Asosiy kontentga o‘tish": "Skip to main content", "raqamliMuallim": "raqamliMuallim",
    "Attestatsiyagacha": "Until attestation", "kun": "days", "Hech narsa topilmadi.": "Nothing found.",
    "Mavzu, bo‘lim yoki eslatmani qidiring…": "Search topics, sections or notes…", "Qidiruv": "Search",
    "Ekspert paneli": "Expert panel", "Admin paneli": "Admin panel", "Savollar banki": "Question bank",
    "Mavzular va darslar": "Topics and lessons", "E’tirozlar": "Appeals", "Statistika": "Statistics",
    "Foydalanuvchilar": "Users", "Ekspertlar": "Experts", "Sozlamalar": "Settings",

    # Umumiy tugmalar
    "Saqlash": "Save", "Bekor qilish": "Cancel", "Tasdiqlash": "Confirm", "Yopish": "Close", "Orqaga": "Back",
    "O‘chirish": "Delete", "Tahrirlash": "Edit", "Ko‘rish": "View", "Boshlash": "Start", "Davom ettirish": "Continue",
    "Keyingisi": "Next", "To‘xtatish": "Pause", "Yuborish": "Send", "Kod yuborish": "Send code", "Qayta yuborish": "Resend",
    "Ko‘rsatish": "Show", "Yashirish": "Hide", "Tanlang": "Select", "Hammasi": "All", "Keyinroq": "Later",

    # Kirish va ro'yxatdan o'tish
    "Kirish": "Log in", "Parol": "Password", "Parolni takrorlang": "Repeat password", "Parolni tiklash": "Reset password",
    "Yangi parol": "New password", "Joriy parol": "Current password", "Parolni saqlash": "Save password",
    "Ism": "First name", "Familiya": "Last name", "Oxirgi qadam": "Last step", "Ro‘yxatdan o‘tish": "Sign up",
    "Maxfiy so‘z": "Secret word", "Boshqa usul": "Another way", "Tasdiqlash kodi": "Verification code",
    "Telefon raqam yoki email": "Phone number or email", "Email manzil": "Email address",
    "Email orqali tasdiqlash": "Confirm via email", "Raqamni tasdiqlang": "Confirm your number",
    "Telegram botni ochish": "Open Telegram bot", "Telegram botni oching": "Open the Telegram bot",
    "Kodni qayta yuborish": "Resend code", "Kod amal qiladi:": "Code valid for:", "Kod tasdiqlandi": "Code confirmed",
    "Ismingiz sertifikatda shunday yoziladi.": "Your name will appear on the certificate like this.",
    "Kamida 8 ta belgi, harf va raqam": "At least 8 characters, letters and digits",
    "Bu raqam orqali ro‘yxatdan o‘tilmagan. Raqamni tekshiring yoki email orqali tiklang":
        "No account is registered with this number. Check the number or reset via email",
    "Kodning amal qilish muddati (5 daqiqa) tugadi. Yangi kod so‘rang.": "The code has expired (5 minutes). Request a new code.",

    # Sertifikat
    "Sertifikatni tekshirish": "Verify certificate", "Sertifikat haqiqiy.": "The certificate is valid.",
    "Sertifikat muddati o‘tgan.": "The certificate has expired.", "05.01.2026 dan boshlab amal qilmaydi.": "Not valid since 05.01.2026.",
    "Sabab:": "Reason:", "sertifikat berilgan kundan boshlab 3 yil amal qiladi (berilgan sana: 05.01.2023).":
        "a certificate is valid for 3 years from the issue date (issued: 05.01.2023).",

    # Bosh sahifa
    "Salom,": "Hello,", "Attestatsiya": "Attestation", "kun qoldi": "days left", "Darsni davom ettirish": "Continue the lesson",
    "Keyingi mavzu": "Next topic", "Majburiy nazorat testini boshlash": "Start the mandatory control test",
    "Attestatsiyaga tayyorlik": "Attestation readiness", "Xato qilayotgan mavzularingiz": "Topics you make mistakes in",
    "Oldingi testlaringiz bo‘yicha xatolik foizi": "Error rate based on your previous tests", "daqiqa": "minutes", "daq": "min",
    "Bugun kichik qadam — ertaga katta natija.": "A small step today — a big result tomorrow.",
    "Har bir to‘g‘ri javob sizni maqsadga yaqinlashtiradi.": "Every correct answer brings you closer to your goal.",
    "Bilim — eng ishonchli sarmoya.": "Knowledge is the most reliable investment.",
    "Xato qilish — o‘rganishning bir qismi.": "Making mistakes is part of learning.",
    "Izchillik iqtidordan kuchliroq.": "Consistency beats talent.",
    "Bugun o‘rgangan narsangiz ertangi darsingizni boyitadi.": "What you learn today enriches tomorrow’s lesson.",
    "Oz-ozdan, lekin har kuni.": "Little by little, but every day.",
    "Siz uddalaysiz — attestatsiya yaqin!": "You can do it — attestation is near!",

    # O'quv reja
    "O‘zlashtirish holati": "Mastery status", "Hozirgi mavzu": "Current topic", "Qayta o‘zlashtirish": "Relearn",
    "Qayta o‘zlashtirish tavsiya etiladi": "Relearning is recommended", "Majburiy": "Mandatory", "Ixtiyoriy": "Optional",
    "O‘zlashtirilmagan": "Not mastered", "O‘rganilmoqda": "In progress", "Qayta o‘zlashtirish kerak": "Needs relearning",
    "O‘zlashtirilgan": "Mastered", "Mustahkam": "Solid",

    # Testlar va natijalar
    "Testni boshlash": "Start a test", "Attestatsiya testi": "Attestation test", "Haftalik test": "Weekly test",
    "Ixtiyoriy test": "Optional test", "Test turlari haqida": "About test types", "Savollar va javoblar": "Questions and answers",
    "Testni qayta topshirish": "Retake the test", "Qayta topshirish": "Retake", "Sizning javobingiz": "Your answer",
    "To‘g‘ri javob": "Correct answer", "To‘g‘ri": "Correct", "Xato": "Wrong", "Javobsiz": "Unanswered",
    "Xatolar ustida ishlash": "Work on mistakes", "Xatolaringizga o‘xshash testlar bajarish": "Practice tests similar to your mistakes",
    "Testga o‘tish": "Go to test", "Nechta test ishlaysiz?": "How many questions?",
    "Mavzular bo‘yicha o‘zlashtirish": "Mastery by topic", "Tavsiya": "Recommendation",
    "E’tirozni o‘chirish": "Delete appeal", "E’tiroz o‘chirildi": "Appeal deleted",

    # Dam olish
    "Ko‘zlaringizga dam bering": "Give your eyes a rest", "5 daqiqa dam olish": "Take a 5-minute break",
    "Tanaffus": "Break", "Majburiy tanaffus": "Mandatory break",
    "Siz tizimdan 45 daqiqa foydalandingiz. Endi 5 daqiqa davomida ko‘zlaringizga dam bering: kamida 20 soniya davomida taxminan 6 metr uzoqlikdagi narsaga qarang. Bu ko‘z mushaklarini bo‘shashtiradi va ko‘z charchashi, qurishi hamda bosh og‘rig‘ining oldini oladi.":
        "You have been using the system for 45 minutes. Now rest your eyes for 5 minutes: look at something about 6 metres away for at least 20 seconds. This relaxes the eye muscles and prevents eye strain, dryness and headaches.",

    # Ekspert
    "Tekshiruv navbati": "Review queue", "Savol yaratish": "Create question", "Savol qo‘shish": "Add question",
    "Rad etish": "Reject", "Mavzu yaratish": "Create topic", "Dars qo‘shish": "Add lesson", "Havola biriktirish": "Attach link",
    "Mavzu": "Topic", "Dars": "Lesson", "Qiyinlik darajasi": "Difficulty", "Savol turi": "Question type", "Savol formati": "Question format",
    "Savol matni": "Question text", "Oson": "Easy", "O‘rta": "Medium", "Qiyin": "Hard",
}
