"""Interfeys asosiy qismining ruscha tarjimasi (menyu, kirish, xatolar, holatlar, testlar, admin/ekspert xabarlari).

scripts/apply_translations.py shu lug'atni ru/LC_MESSAGES/messages.po ga yozadi.
Qolgan satrlar (dars matnlari, maxfiylik siyosati va h.k.) tarjimonga beriladi; tarjima bo'lmasa o'zbekcha ko'rinadi.
"""

RU = {
    # Forma xatolari
    "Maydonni to‘ldiring": "Заполните поле",
    "Telefon raqam noto‘g‘ri: +998 va 9 ta raqam bo‘lishi kerak": "Неверный номер: нужен код +998 и 9 цифр",
    "Email manzil noto‘g‘ri": "Неверный адрес email",
    "Telefon raqam yoki emailni kiriting": "Введите номер телефона или email",
    "Parol kamida 8 ta belgidan iborat bo‘lsin": "Пароль должен содержать не менее 8 символов",
    "Parolda harf ham, raqam ham bo‘lsin": "Пароль должен содержать буквы и цифры",
    "6 xonali kodni to‘liq kiriting": "Введите 6-значный код полностью",
    "Ismni kiriting": "Введите имя",
    "Familiyani kiriting": "Введите фамилию",
    "Ism faqat harflardan iborat bo‘lsin": "Имя должно состоять только из букв",
    "Familiya faqat harflardan iborat bo‘lsin": "Фамилия должна состоять только из букв",
    "Sanani tanlang": "Выберите дату",
    "Sana o‘tib ketgan bo‘lmasin": "Дата не должна быть в прошлом",
    "Xatolarni tuzating": "Исправьте ошибки",
    "Parollar bir xil emas": "Пароли не совпадают",
    "Viloyatni ro‘yxatdan tanlang": "Выберите область из списка",
    "Davom etish uchun rozilik kerak": "Для продолжения нужно согласие",
    "Kod noto‘g‘ri. Namunada kod: 123456": "Неверный код. В демо-версии код: 123456",
    "Yangi parol joriy paroldan farq qilsin": "Новый пароль должен отличаться от текущего",
    "Sababni tanlang": "Выберите причину",
    "Izoh 1000 belgidan oshmasin": "Комментарий — не более 1000 символов",
    "«Boshqa» sababini izohda yozing": "Опишите причину «Другое» в комментарии",
    "Xabarni yozing": "Напишите сообщение",
    "Xabar 2000 belgidan oshmasin": "Сообщение — не более 2000 символов",
    "Qaydni yozing": "Напишите заметку",
    "Qayd 5000 belgidan oshmasin": "Заметка — не более 5000 символов",
    "Kod 5000 belgidan oshmasin": "Код — не более 5000 символов",
    "Ism va familiyani kiriting": "Введите имя и фамилию",
    "Kamida bitta yo‘nalishni tanlang": "Выберите хотя бы одно направление",
    "Kamida bitta huquq bering": "Назначьте хотя бы одно право",

    # Muvaffaqiyat xabarlari
    "Xush kelibsiz!": "Добро пожаловать!",
    "Kod %(email)s manziliga yuborildi": "Код отправлен на %(email)s",
    "Ro‘yxatdan o‘tdingiz. Eslatma: 6 oy kirilmasa akkaunt avtomatik o‘chiriladi":
        "Вы зарегистрированы. Напоминание: если не входить 6 месяцев, аккаунт удаляется автоматически",
    "Google akkaunti orqali kirdingiz (namuna)": "Вы вошли через Google (демо)",
    "Parol yangilandi. Yangi parol bilan kiring": "Пароль обновлён. Войдите с новым паролем",
    "Tasdiqlash kodi yuborildi": "Код подтверждения отправлен",
    "Shaxsiy ma’lumotlar saqlandi": "Личные данные сохранены",
    "Parol o‘zgartirildi": "Пароль изменён",
    "Hudud saqlandi": "Регион сохранён",
    "E’tirozingiz qabul qilindi. Ekspert xulosasi «E’tirozlarim» bo‘limida ko‘rinadi":
        "Апелляция принята. Решение эксперта появится в разделе «Мои апелляции»",
    "Fikringiz qo‘shildi": "Комментарий добавлен",
    "Eslatma saqlandi": "Заметка сохранена",
    "Foydalanuvchi bloklandi": "Пользователь заблокирован",
    "Foydalanuvchi blokdan chiqarildi": "Пользователь разблокирован",
    "Parolni tiklash havolasi yuborildi": "Ссылка для сброса пароля отправлена",
    "Akkaunt o‘chirildi": "Аккаунт удалён",
    "%(name)s ekspert sifatida qo‘shildi. Taklifnoma yuborildi": "%(name)s добавлен(а) как эксперт. Приглашение отправлено",
    "Ekspert faoliyati to‘xtatildi": "Работа эксперта приостановлена",
    "Ekspert faollashtirildi": "Эксперт активирован",
    "Huquqlar saqlandi": "Права сохранены",
    "%(name)s uchun attestatsiya sanasi saqlandi": "Дата аттестации для %(name)s сохранена",
    "Foydalanuvchi": "Пользователь",

    # API
    "Urinish identifikatori noto‘g‘ri": "Неверный идентификатор попытки",
    "Test turi noto‘g‘ri": "Неверный тип теста",
    "Javoblar soni noto‘g‘ri": "Неверное количество ответов",
    "Ba’zi javoblar noto‘g‘ri formatda": "Некоторые ответы в неверном формате",
    "Urinish turi mos kelmaydi": "Тип попытки не совпадает",
    "Urinish yakunlangan, javoblarni o‘zgartirib bo‘lmaydi": "Попытка завершена, ответы изменить нельзя",

    # Menyu
    "Bosh sahifa": "Главная", "O‘quv reja": "Учебный план", "Bilim darajasi": "Уровень знаний",
    "Natijalarim": "Мои результаты", "O‘qish": "Обучение", "AI tutor": "AI-тьютор", "Eslatmalar": "Заметки",
    "Muhokamalar": "Обсуждения", "Test va natijalar": "Тесты и результаты", "Testlarim": "Мои тесты",
    "Attestatsiya sinovi": "Пробная аттестация", "Xatolar analitikasi": "Анализ ошибок",
    "E’tirozlarim": "Мои апелляции", "Sertifikatlarim": "Мои сертификаты",
    "Tekshiruv navbati": "Очередь проверки", "Savollar banki": "Банк вопросов", "Savol yaratish": "Создать вопрос",
    "Mavzular va darslar": "Темы и уроки", "E’tirozlar": "Апелляции", "Statistika": "Статистика",
    "Foydalanuvchilar": "Пользователи", "Ekspertlar": "Эксперты", "Sozlamalar": "Настройки",
    "Reja": "План", "Bilim": "Знания", "Yana": "Ещё",

    # Holatlar
    "O‘zlashtirilmagan": "Не изучено", "O‘rganilmoqda": "Изучается", "Qayta o‘zlashtirish kerak": "Нужно повторить",
    "O‘zlashtirilgan": "Изучено", "Mustahkam": "Закреплено", "O‘tdi": "Сдано", "Tavsiya bilan": "С рекомендацией",
    "Qaytarildi": "Не сдано", "Ko‘rib chiqilmoqda": "На рассмотрении", "Qabul qilindi": "Принято", "Rad etildi": "Отклонено",
    "Reja bo‘yicha": "По плану",
    "Hozirgi sur’atda attestatsiyadan {m} kun oldin tayyor bo‘lasiz.": "В текущем темпе вы будете готовы за {m} дн. до аттестации.",
    "Biroz ortda": "Немного отстаёте",
    "Sur’at sekinlashdi: attestatsiyaga zo‘rg‘a ulgurasiz. Kuniga 15 daqiqa qo‘shing.":
        "Темп снизился: успеваете к аттестации впритык. Добавьте 15 минут в день.",
    "Ortda qolmoqda": "Отстаёте",
    "Hozirgi sur’atda attestatsiyaga ulgurmaysiz. Rejani tezlashtiring.": "В текущем темпе вы не успеете к аттестации. Ускорьте план.",
    "Tasdiqlangan": "Утверждён", "Tekshiruvda": "На проверке", "Qoralama": "Черновик", "Arxivlangan": "В архиве",
    "To‘xtatilgan": "Приостановлен",
    "Savol yaratish va tahrirlash": "Создание и редактирование вопросов",
    "Savollarni tekshirish va tasdiqlash": "Проверка и утверждение вопросов",
    "Mavzular va darslarni tahrirlash": "Редактирование тем и уроков",
    "E’tirozlarni ko‘rib chiqish": "Рассмотрение апелляций",

    # Umumiy UI
    "Nusxa": "Копировать", "Fayl yoki rasm qo‘shish": "Добавить файл или изображение", "Ovozli savol": "Голосовой вопрос",
    "Yuborish": "Отправить", "AI javobini darslik bilan tekshiring. Shaxsiy ma’lumotlaringizni yozmang.":
        "Сверяйте ответ AI с учебником. Не пишите личные данные.",
    "Yopish": "Закрыть", "Savollar": "Вопросы", "Bildirishnomalar": "Уведомления", "Sozlash": "Настроить",
    "Parolni tiklash": "Восстановление пароля", "Attestatsiyaga tayyorlik": "Готовность к аттестации", "Natija": "Результат",
    "Viloyat": "Область", "Orqaga": "Назад", "Mavzu rangini almashtirish": "Сменить тему оформления",
    "Xato": "Ошибка", "Qayta urinish": "Повторить", "Savol": "Вопрос", "Oson": "Лёгкий", "O‘rta": "Средний", "Qiyin": "Сложный",
    "Asosiy menyu": "Главное меню", "Menyuni yopish": "Закрыть меню", "Attestatsiyagacha": "До аттестации", "kun": "дн.",
    "Menyuni ochish": "Открыть меню", "Qidirish (Ctrl+K)": "Поиск (Ctrl+K)", "Pastki menyu": "Нижнее меню",
    "Hammasini o‘qilgan deb belgilash": "Отметить все как прочитанные", "Telegram orqali ham yuboriladi ·": "Дублируется в Telegram ·",
    "Tezkor qidiruv": "Быстрый поиск", "Mavzu, bo‘lim yoki eslatmani qidiring…": "Найдите тему, раздел или заметку…",
    "Qidiruv": "Поиск", "Hech narsa topilmadi.": "Ничего не найдено.", "AI tutordan so‘rash": "Спросить AI-тьютора",
    "/ 3 qadam": "/ 3 шаг", "Panel menyusi": "Меню панели", "Chiqish": "Выйти",
    "Ilovani telefoningizga o‘rnating": "Установите приложение на телефон",
    "Bosh ekrandan bir bosishda ochiladi, internet bo‘lmaganda ham darslar va boshlangan test ishlaydi.":
        "Открывается с главного экрана, уроки и начатый тест работают без интернета.",
    "Keyinroq": "Позже", "Safari pastidagi": "Нажмите кнопку", "Ulashish": "Поделиться", "tugmasini bosing": "внизу Safari",
    "«Bosh ekranga qo‘shish»": "«На экран „Домой“»", "(Add to Home Screen) bandini tanlang": "(Add to Home Screen)",
    "O‘ng yuqoridagi": "Нажмите", "«Qo‘shish»": "«Добавить»", "ni bosing": "в правом верхнем углу",
    "O‘rnatish": "Установить", "Yuklanmoqda…": "Загрузка…", "Tezkor yordam": "Быстрая помощь", "To‘liq ekran": "Полный экран",
    "Qolgan vaqt": "Осталось времени", "To‘xtatish": "Пауза", "E’tiroz bildirish": "Подать апелляцию",
    "Tushunarli": "Понятно", "Bugun": "Сегодня", "daqiqa": "мин", "daq": "мин", "yoki": "или", "Tanlang": "Выберите",

    # Kirish va ro'yxatdan o'tish
    "Ma’lumotlaringiz": "Ваши данные", "Oxirgi qadam": "Последний шаг",
    "Ismingiz sertifikatda shunday yoziladi.": "Так ваше имя будет указано в сертификате.",
    "Ism": "Имя", "Familiya": "Фамилия", "Parol": "Пароль", "Kamida 8 ta belgi, harf va raqam": "Не менее 8 символов, буквы и цифры",
    "Parolni ko‘rsatish": "Показать пароль", "Parolni takrorlang": "Повторите пароль", "Hudud (ixtiyoriy)": "Регион (необязательно)",
    "Tuman": "Район", "Muhim:": "Важно:", "akkauntingizga": "если в аккаунт не входить",
    "davomida kirilmasa, u ma’lumotlari bilan birga avtomatik o‘chiriladi. O‘chirishdan 2 hafta oldin Telegram va email orqali ogohlantiramiz.":
        ", он будет автоматически удалён вместе с данными. За 2 недели до удаления предупредим в Telegram и по email.",
    "6 oy": "6 месяцев",
    "Shaxsiy ma’lumotlarimni qayta ishlashga roziman va": "Я согласен(на) на обработку персональных данных и принимаю",
    "maxfiylik siyosati": "политику конфиденциальности", "ni qabul qilaman.": ".",
    "Ro‘yxatdan o‘tish": "Регистрация", "Xush kelibsiz": "Добро пожаловать", "Attestatsiyaga": "Готовьтесь к аттестации",
    "AI bilan": "вместе с AI", "tayyorlaning": " ",
    "Informatika o‘qituvchilari uchun: bilimingizni aniqlaymiz, shaxsiy reja tuzamiz va AI tutor bilan birga o‘qiysiz.":
        "Для учителей информатики: определим ваш уровень, составим личный план, а учиться будете вместе с AI-тьютором.",
    "Kirish": "Войти", "Diagnostika": "Диагностика", "Shaxsiy reja": "Личный план",
    "Qaytganingizdan xursandmiz": "Рады вас видеть снова", "Telefon raqam yoki email va parolingizni kiriting.":
        "Введите номер телефона или email и пароль.",
    "Telefon raqam yoki parol noto‘g‘ri. Yana": "Неверный номер или пароль. Осталось", "2 ta": "2",
    "urinish qoldi, keyin akkaunt 15 daqiqaga bloklanadi.": "попытки, затем аккаунт будет заблокирован на 15 минут.",
    "Telefon raqam yoki email": "Номер телефона или email", "Parolni unutdingizmi?": "Забыли пароль?", "Parolingiz": "Ваш пароль",
    "Akkauntingiz yo‘qmi?": "Нет аккаунта?", "Maxfiylik siyosati": "Политика конфиденциальности",
    "Telefon raqamingizni kiriting. Uni Telegram bot orqali tasdiqlaymiz.": "Введите номер телефона. Подтвердим его через Telegram-бот.",
    "Telefon raqam": "Номер телефона",
    "Bu raqam ro‘yxatdan o‘tgan bo‘lsa, kirish yoki parolni tiklashni taklif qilamiz.":
        "Если номер уже зарегистрирован, предложим войти или восстановить пароль.",
    "Telegram orqali davom etish": "Продолжить через Telegram", "Email orqali ro‘yxatdan o‘tish": "Регистрация по email",
    "Akkauntingiz bormi?": "Уже есть аккаунт?",
    "Telefon raqam yoki emailingizni kiriting, kodni Telegram yoki email orqali yuboramiz.":
        "Введите номер или email — пришлём код в Telegram или на почту.",
    "Kodni va yangi parolni kiriting.": "Введите код и новый пароль.",
    "+998 90 123 45 67 yoki email@maktab.uz": "+998 90 123 45 67 или email@maktab.uz",
    "Kod yuborish": "Отправить код", "Tasdiqlash kodi": "Код подтверждения", "6 xonali kod": "6-значный код",
    "Namunada kod: 123456": "В демо-версии код: 123456", "Yangi parol": "Новый пароль", "Parolni saqlash": "Сохранить пароль",
    "Boshqa raqam yoki email kiritish": "Ввести другой номер или email",
    "Email orqali tasdiqlash": "Подтверждение по email",
    "Kodni emailingizga yuboramiz. Keyin shu email bilan tizimga kirasiz.": "Отправим код на почту. Затем вы будете входить с этим email.",
    "Email manzil": "Адрес email", "Kod 15 daqiqa amal qiladi. Xat kelmasa, «Spam» papkasini tekshiring.":
        "Код действует 15 минут. Если письма нет, проверьте папку «Спам».",
    "Tasdiqlash": "Подтвердить", "Raqamni tasdiqlash": "Подтверждение номера", "Raqamni tasdiqlang": "Подтвердите номер",
    "raqami uchun uch qadam:": "— три шага:", "Telegram botni oching": "Откройте Telegram-бот",
    "«Telefon raqamni ulashish» tugmasini bosing": "Нажмите «Поделиться номером телефона»",
    "Bot yuborgan 6 xonali kodni kiriting": "Введите 6-значный код из бота", "Telegram botni ochish": "Открыть Telegram-бот",
    "Kod 5 daqiqa amal qiladi. 5 ta urinish bor. Namunada kod: 123456": "Код действует 5 минут, 5 попыток. В демо-версии код: 123456",
    "Telegram boshqa raqamga ulanganmi? Bot sizga": "Telegram привязан к другому номеру? Бот предложит",
    "Telegram’dagi raqam bilan davom etish": "продолжить с номером из Telegram", "ni taklif qiladi.": ".",
    "Kodni qayta yuborish": "Отправить код повторно",

    # Sertifikatni tekshirish
    "Sertifikatni tekshirish": "Проверка сертификата", "Sertifikat haqiqiy.": "Сертификат действителен.",
    "raqamliMuallim platformasi tomonidan berilgan.": "Выдан платформой raqamliMuallim.", "Egasi": "Владелец", "Kurs": "Курс",
    "Informatika o‘qituvchilarini": "Подготовка учителей информатики", "attestatsiyaga tayyorlash": "к аттестации",
    "Umumiy natija": "Общий результат", "Mavzular": "Темы", "Berilgan sana": "Дата выдачи",
    "Sertifikat davlat attestatsiyasi hujjati hisoblanmaydi. U kursni to‘liq o‘zlashtirib, yakuniy diagnostikadan o‘tganlikni tasdiqlaydi.":
        "Сертификат не является документом государственной аттестации. Он подтверждает полное прохождение курса и итоговой диагностики.",
    "Sertifikat bekor qilingan.": "Сертификат аннулирован.", "05.01.2027 dan boshlab amal qilmaydi.": "Недействителен с 05.01.2027.",
    "Sabab:": "Причина:", "yakuniy diagnostika natijasi e’tiroz ko‘rib chiqilgandan keyin qayta hisoblandi.":
        "результат итоговой диагностики пересчитан после рассмотрения апелляции.",
    "Bunday raqamli sertifikat topilmadi.": "Сертификат с таким номером не найден.", "Raqamni tekshirib, qayta kiriting.": "Проверьте номер и введите снова.",
    "Boshqa sertifikatni tekshirish": "Проверить другой сертификат", "Masalan: INF-2026-000123": "Например: INF-2026-000123",
    "Tekshirish": "Проверить",

    # Test
    "To‘xtatish va chiqish (javoblar saqlanadi)": "Пауза и выход (ответы сохранятся)", "1-bosqich · Oson": "Этап 1 · Лёгкий",
    "To‘liq ekran (faqat test oynasi)": "Полный экран (только окно теста)",
    "Internet yo‘q. Javoblaringiz qurilmada saqlanmoqda va internet tiklanganda yuboriladi.":
        "Нет интернета. Ответы сохраняются на устройстве и будут отправлены при подключении.",
    "Mavzu:": "Тема:", "Bitta javobni tanlang": "Выберите один ответ", "Bir nechta javobni belgilang": "Отметьте несколько ответов",
    "Tanlang…": "Выберите…", "Javobingiz": "Ваш ответ", "Raqamli klaviatura": "Цифровая клавиатура", "Keyingisi": "Далее",
    "umumiy ball": "общий балл", "Bu mavzuni yana bir bor o‘rganamiz": "Изучим эту тему ещё раз",
    "2-bosqichdan o‘tish uchun 80%% kerak edi. Xato qilgan qismlaringizdan boshlaymiz.":
        "Для прохождения этапа 2 нужно было 80%%. Начнём с разделов, где были ошибки.",
    "Keyingi mavzuga o‘tishingiz mumkin": "Можно переходить к следующей теме",
    "Natija 70–89%% oralig‘ida, shuning uchun mavzuni keyinroq takrorlashni tavsiya qilamiz.":
        "Результат 70–89%%, поэтому рекомендуем позже повторить тему.",
    "Xato qilingan qismlar": "Разделы с ошибками", "Mavzular bo‘yicha": "По темам", "-savol": "-й вопрос", "To‘g‘ri": "Верно",
    "Sizning javobingiz:": "Ваш ответ:", "To‘g‘ri javob:": "Правильный ответ:", "Izoh.": "Пояснение.",
    "Xatoimni tushuntir": "Объясни мою ошибку", "(Mavzu:": "(Тема:", "Darsga qaytish": "Вернуться к уроку", "Keyingi mavzu": "Следующая тема",
    "Sabab": "Причина", "Izoh (ixtiyoriy)": "Комментарий (необязательно)", "Shoshilinch: xato yaqqol ko‘rinib turibdi": "Срочно: ошибка очевидна",
    "E’tirozingiz qabul qilindi": "Апелляция принята", "Ekspert xulosasi «E’tirozlarim» bo‘limida ko‘rinadi.": "Решение эксперта появится в разделе «Мои апелляции».",
    "1-bosqichdan o‘tdingiz": "Этап 1 пройден", "O‘tish uchun 90%% kerak edi.": "Для прохождения нужно было 90%%.",
    "Keyingi bosqich": "Следующий этап",
    "10 ta o‘rta darajadagi savol, 15 daqiqa. Savollar biroz murakkabroq bo‘ladi, shoshilmang.":
        "10 вопросов среднего уровня, 15 минут. Вопросы немного сложнее — не торопитесь.",
    "2-bosqichni boshlash": "Начать этап 2", "Boshlash": "Начать",

    # Bosh sahifa
    "Attestatsiya": "Аттестация", "kun qoldi": "дн. осталось", "Salom,": "Здравствуйте,", "Bugun nimani o‘rganamiz?": "Что изучим сегодня?",
    "AI tutorga savol bering…": "Задайте вопрос AI-тьютору…", "elif va else farqi nima?": "Чем elif отличается от else?",
    "Xatolarimni tahlil qil": "Разбери мои ошибки", "Sikllarga masala ber": "Дай задачу на циклы", "Eslatma:": "Напоминание:",
    "akkauntga": "если в аккаунт не входить", "davomida kirilmasa, u avtomatik o‘chiriladi. Undan 2 hafta oldin ogohlantiramiz.":
        ", он будет удалён автоматически. Предупредим за 2 недели.",
    "3 qadamda tayyorgarlikni boshlang": "Начните подготовку за 3 шага",
    "Uchala qadam bajarilgach, bu yerda shaxsiy rejangiz va tayyorlik ko‘rsatkichi chiqadi.":
        "После трёх шагов здесь появятся ваш личный план и показатель готовности.",
    "Tayyor:": "Готовность:", "Attestatsiya:": "Аттестация:", "Keyingi qadam": "Следующий шаг",
    "Darsni davom ettirish": "Продолжить урок", "Bugun ·": "Сегодня ·",
    "Darslar orasidagi qisqa vaqtga mo‘ljallangan": "Рассчитано на короткие перерывы между уроками",
    "Siz «elif zanjiri»da ko‘proq xato qilyapsiz. Darsni shu qismdan davom ettiring, keyin mavzu testini topshiring.":
        "Больше всего ошибок в «цепочке elif». Продолжите урок с этого места, затем сдайте тест по теме.",

    # Til tanlash
    "Interfeys tili": "Язык интерфейса", "Rus tili tarjimasi to‘ldirilmoqda": "Перевод на русский дополняется",
    "Ko‘rinish": "Внешний вид", "Yorug‘ / qorong‘i mavzu": "Светлая / тёмная тема",
    "Google orqali kirish": "Войти через Google", "Google orqali ro‘yxatdan o‘tish": "Регистрация через Google",
}
