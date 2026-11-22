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
    "Interfeys tili": "Interface language", "O‘zbek, rus va ingliz tillari": "Uzbek, Russian and English", "Asosiy kontentga o‘tish": "Skip to main content", "raqamliMuallim": "raqamliMuallim",
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

# JS (core.js → rmT) va Alpine ifodalaridagi matnlar
EN.update({
    "Saqlanmoqda…": "Saving…", "Qurilmada saqlandi": "Saved on device", "Saqlandi": "Saved", "Saqlanmadi": "Not saved",
    "Server javobini o‘qib bo‘lmadi": "Could not read the server response", "Xatolarni tuzating": "Please fix the errors",
    "Internetga ulanib bo‘lmadi. Ulanishni tekshirib, qayta yuboring.": "No internet connection. Check your connection and try again.",
    "Internetga ulanib bo‘lmadi": "No internet connection",
    "Brauzer menyusidan «Ilovani o‘rnatish»ni tanlang": "Choose “Install app” from the browser menu",
    "Bu namunaviy javob. Backend ulanganda AI tutor «%(q)s» savoliga darslik asosida javob beradi.": "This is a sample answer. Once the server is connected, the AI tutor will answer “%(q)s” based on the textbook.",
    "Bo‘limlar": "Sections", "Mavzular": "Topics", "Eslatmalar": "Notes", "Nusxalandi": "Copied",
    "So‘nggi o‘qigan joyingiz:": "You stopped at:", "Boshidan": "From the start",
    "Belgilangan matn": "Selected text", "Eslatmaga saqlash": "Save to notes", "AI’dan so‘rash": "Ask AI",
    "Umumiy": "General", "Bugun": "Today", "Eslatmalarga saqlandi": "Saved to notes",
    "Tushuntirib bering: «%(t)s»": "Explain: “%(t)s”", "Tanaffus tugadi. Davom etamiz!": "Break is over. Let’s continue!",
    "Parolni yashirish": "Hide password", "Parolni ko‘rsatish": "Show password",
    "Yo‘riqnomani yopish": "Close instructions", "Qanday o‘rnatiladi?": "How to install?", "O‘rnatish": "Install",
    "-savol": " question", "javob berilgan": "answered", "Izoh (ixtiyoriy)": "Comment (optional)", "Izoh": "Comment",
    "Nima uchun shunday deb hisoblaysiz?": "Why do you think so?",
    "Havola nusxalandi ✓": "Link copied ✓", "Havolani ulashish": "Share link",
    "Sertifikatni tekshirish uchun QR-kod": "QR code to verify the certificate", "Muhr": "Seal",
    "Fikringizni yozing…": "Write your comment…", "Fikringiz": "Your comment", "Pauza": "Pause", "Ijro": "Play",
    "Hech narsa topilmadi": "Nothing found", "Hali eslatma yo‘q": "No notes yet",
    "Eslatmani tahrirlash": "Edit note", "Yangi eslatma": "New note",
    "Kod blokini olib tashlash": "Remove code block", "Kod bloki qo‘shish": "Add code block",
    "Eslab qolmoqchi bo‘lgan narsangizni yozing…": "Write down what you want to remember…", "Kod": "Code",
    "Safari: Ulashish → Bosh ekranga qo‘shish": "Safari: Share → Add to Home Screen",
    "Bosh ekrandan ochiladi, oflayn ishlaydi": "Opens from the home screen, works offline",
    "AI tutorga savol bering…": "Ask the AI tutor…", "Ekspert xulosasi": "Expert conclusion",
    "Xulosa barcha e’tiroz bildirganlarga yuboriladi…": "The conclusion will be sent to everyone who appealed…",
    "Informatika o‘qituvchilarini attestatsiyaga moslashuvchan tayyorlash platformasi": "Adaptive certification prep platform for computer science teachers",
    "Muhokama": "Discussion", "AI tutor": "AI tutor", "Yuklanmoqda…": "Loading…",
    "Profil va sozlamalar": "Profile and settings", "Ixtiyoriy test": "Optional test", "Diagnostika": "Diagnostics",
})

# Xato sahifalari (errors/error.html)
EN.update({
    "Sahifa muddati o‘tdi": "Page expired",
    "Xavfsizlik uchun forma eskirdi yoki so‘rov noto‘g‘ri. Sahifani yangilab, qayta yuboring.": "For security, the form has expired or the request is invalid. Refresh the page and submit again.",
    "Sahifa topilmadi": "Page not found",
    "Havola eskirgan yoki manzilda xato bor. Bosh sahifadan kerakli bo‘limni toping.": "The link is outdated or the address is wrong. Find the section you need from the home page.",
    "Bu sahifaga ruxsat yo‘q": "You don’t have access to this page",
    "Sahifa boshqa rol (ekspert yoki administrator) uchun. Boshqa akkaunt bilan kirib ko‘ring.": "This page is for another role (expert or administrator). Try signing in with a different account.",
    "Nimadir noto‘g‘ri ketdi": "Something went wrong",
    "Xato bizning tomonda. Javoblaringiz va progress saqlangan. Bir daqiqadan keyin qayta urinib ko‘ring.": "The error is on our side. Your answers and progress are saved. Please try again in a minute.",
})

# Ekspert taklifnomasi, ekspert va admin profili
EN.update({
    'Ekspert (metodist)': 'Expert (methodologist)',
    'Administrator': 'Administrator',
    'Nusxalab oling:': 'Copy this:',
    'Javob kutayotgan taklifnomalar': 'Pending invitations',
    'Telegram orqali': 'via Telegram',
    'Email orqali': 'via email',
    'yuborildi:': 'sent:',
    'Havolani nusxalash': 'Copy link',
    'Ekspert qo‘shish': 'Add expert',
    'Faoliyatini to‘xtatish': 'Suspend',
    'Faollashtirish': 'Activate',
    'Ism va familiya': 'First and last name',
    'Telefon yoki email (login)': 'Phone or email (login)',
    'Taklif havolasi shu raqamga ulangan Telegram orqali yuboriladi. Ekspert havolani ochib, parolni o‘zi o‘rnatadi.': 'The invitation link will be sent via the Telegram account linked to this number. The expert opens it and sets their own password.',
    'Taklif havolasi shu emailga xat bilan yuboriladi. Ekspert havolani ochib, parolni o‘zi o‘rnatadi.': 'The invitation link will be emailed to this address. The expert opens it and sets their own password.',
    'Ekspert shu telefon raqam yoki email bilan tizimga kiradi. Taklif havolasi shu manzilga yuboriladi.': 'The expert will sign in with this phone number or email. The invitation link is sent there.',
    'Qo‘shish va taklif yuborish': 'Add and send invitation',
    'Admin': 'Admin',
    'Ekspert': 'Expert',
    'Akkaunt': 'Account',
    'Ekspert taklifnomasi': 'Expert invitation',
    'Ekspert sifatida taklif qilindingiz': 'You’ve been invited as an expert',
    'Akkauntingizni faollashtirish uchun parol o‘rnating. Parolni faqat siz bilasiz — administrator uni ko‘rmaydi.': 'Set a password to activate your account. Only you know it — the administrator can’t see it.',
    'Login': 'Login',
    'Kamida 8 ta belgi, harf va raqam aralash bo‘lsin.': 'At least 8 characters, letters and numbers.',
    'Telefon yoki emailingizga kira olmasangiz, akkauntni shu so‘z orqali tiklaysiz. Katta-kichik harf farqlanmaydi.': 'If you lose access to your phone or email, you can recover the account with this word. Not case-sensitive.',
    'Akkauntni faollashtirish': 'Activate account',
    'Havola 72 soat amal qiladi va faqat bir marta ishlatiladi.': 'The link is valid for 72 hours and can be used once.',
    'Akkaunt allaqachon faollashtirilgan': 'Account already activated',
    'Taklif havolasining muddati o‘tgan': 'The invitation link has expired',
    'Taklif havolasi yaroqsiz': 'The invitation link is invalid',
    'Bu havola orqali parol o‘rnatilgan. Telefon raqam yoki email va parolingiz bilan kiring.': 'A password has already been set with this link. Sign in with your phone or email and password.',
    'Havola 72 soat amal qiladi. Administratordan taklifnomani qayta yuborishni so‘rang.': 'The link is valid for 72 hours. Ask the administrator to resend the invitation.',
    'Havola to‘liq nusxalanmagan yoki bekor qilingan. Xabardagi havolani qayta oching yoki administratorga murojaat qiling.': 'The link is incomplete or has been revoked. Open the link from the message again or contact the administrator.',
    'Kirish sahifasi': 'Sign-in page',
    'Ekspert paneli': 'Expert panel',
    'Admin paneli': 'Admin panel',
    'Profil': 'Profile',
    'Shaxsiy ma’lumotlar': 'Personal details',
    'Parolni o‘zgartirish': 'Change password',
    'Yangi parolni takrorlang': 'Repeat new password',
    'Joriy parolni unutdingizmi?': 'Forgot your current password?',
    'Parolni yangilash': 'Update password',
    'Parolni unutsangiz: kirish sahifasidagi «Parolni unutdingizmi?» orqali telefon (Telegram) yoki emailga kelgan kod bilan yangi parol o‘rnatasiz.': 'If you forget your password: on the sign-in page use “Forgot password?” and set a new one with a code sent to Telegram or email.',
    'Taklif havolasi Telegram orqali %(c)s raqamiga yuborildi. Havola 72 soat amal qiladi': 'Invitation link sent via Telegram to %(c)s. Valid for 72 hours',
    'Taklif havolasi %(c)s manziliga yuborildi. Havola 72 soat amal qiladi': 'Invitation link sent to %(c)s. Valid for 72 hours',
    'Bu telefon yoki email bilan ekspert allaqachon bor': 'An expert with this phone or email already exists',
    'Taklifnoma bekor qilindi. Eski havola endi ishlamaydi': 'Invitation cancelled. The old link no longer works',
    'Shartlarga rozilik bildiring': 'Please accept the terms',
    'Akkauntingiz yaratildi. Xush kelibsiz, %(name)s!': 'Your account has been created. Welcome, %(name)s!',
})
