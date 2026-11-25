"""Dastur tugmalari (Word, Excel, PowerPoint, Paint): bitta umumiy ikonka to'plami — o'zimiz chizgan sodda belgilar.

Savolda rasm saqlanmaydi, faqat kod: «word.bold». Kod = dastur + ikonka; nomi savol javobida ishlatiladi, ikonka yonida
ko'rsatilmaydi. Yangi ikonka — shu yerga bitta qator (24×24, chiziqli).
"""
from markupsafe import Markup

PROGRAMS = {"word": "Word", "excel": "Excel", "ppt": "PowerPoint", "paint": "Paint"}

_LINES = '<path d="M4 6h16M4 10h{a}M4 14h16M4 18h{b}"/>'
# ikonka: (dasturlar, nomi, vazifasi, SVG ichi)
ICONS: dict[str, tuple[str, str, str, str]] = {
    "bold": ("word excel ppt", "Qalin", "Belgilangan matnni qalin qiladi", '<path d="M7 5h6a3.5 3.5 0 0 1 0 7H7zM7 12h7a3.5 3.5 0 0 1 0 7H7z" stroke-width="2.6"/>'),
    "italic": ("word excel ppt", "Kursiv", "Belgilangan matnni qiya qiladi", '<path d="M10 5h7M7 19h7M14 5l-4 14"/>'),
    "underline": ("word excel ppt", "Tagiga chizilgan", "Matn tagiga chiziq chizadi", '<path d="M7 4v7a5 5 0 0 0 10 0V4M6 20h12"/>'),
    "strike": ("word", "Ustiga chizilgan", "Matn ustiga chiziq chizadi", '<path d="M4 12h16M16 7a4 3 0 0 0-4-2c-3 0-4 2-4 3s1 2 2 2.5M8 17a4 3 0 0 0 4 2c3 0 4-2 4-3"/>'),
    "align_left": ("word ppt", "Chapga tekislash", "Matnni chap chegara bo‘yicha tekislaydi", _LINES.format(a=10, b=8)),
    "align_center": ("word excel ppt", "O‘rtaga tekislash", "Matnni o‘rtaga tekislaydi", '<path d="M4 6h16M7 10h10M4 14h16M8 18h8"/>'),
    "align_right": ("word ppt", "O‘ngga tekislash", "Matnni o‘ng chegara bo‘yicha tekislaydi", '<path d="M4 6h16M10 10h10M4 14h16M12 18h8"/>'),
    "justify": ("word", "Ikki tomonga tekislash", "Matnni ikkala chegara bo‘yicha tekislaydi", '<path d="M4 6h16M4 10h16M4 14h16M4 18h16"/>'),
    "bullets": ("word ppt", "Belgili ro‘yxat", "Belgili ro‘yxat tuzadi", '<circle cx="5" cy="6" r="1.4"/><circle cx="5" cy="12" r="1.4"/><circle cx="5" cy="18" r="1.4"/><path d="M10 6h10M10 12h10M10 18h10"/>'),
    "numbering": ("word ppt", "Raqamli ro‘yxat", "Raqamlangan ro‘yxat tuzadi", '<path d="M4 4h1.5v4M4 16.5c0-2 3-2 3 0 0 1.500-3 2-3 3.500h3M11 6h9M11 12h9M11 18h9"/>'),
    "font_color": ("word ppt", "Matn rangi", "Belgilangan matn rangini o‘zgartiradi", '<path d="M7 15l5-11 5 11M9 11h6"/><path d="M5 20h14" stroke-width="3.5"/>'),
    "cut": ("word excel ppt", "Qirqib olish", "Belgilanganni qirqib, almashish buferiga oladi", '<circle cx="6" cy="18" r="2.500"/><circle cx="18" cy="18" r="2.500"/><path d="M8 16L18 4M16 16L6 4"/>'),
    "copy": ("word excel ppt", "Nusxa olish", "Belgilangandan almashish buferiga nusxa oladi", '<rect x="8" y="8" width="12" height="12" rx="1.500"/><path d="M16 8V4H4v12h4"/>'),
    "paste": ("word excel ppt", "Joylashtirish", "Buferdagini joylashtiradi", '<rect x="5" y="5" width="14" height="16" rx="1.500"/><path d="M9 3h6v4H9zM9 13h6M9 17h4"/>'),
    "painter": ("word excel ppt", "Formatdan nusxa", "Bir matn formatini boshqasiga ko‘chiradi", '<rect x="5" y="3" width="13" height="6" rx="1"/><path d="M18 6h2v6h-8v3M10.500 15h3v6h-3z"/>'),
    "undo": ("word excel ppt paint", "Bekor qilish", "Oxirgi amalni bekor qiladi", '<path d="M8 5L4 9l4 4M4 9h10a5.500 5.500 0 0 1 0 11H9"/>'),
    "redo": ("word excel ppt paint", "Qaytarish", "Bekor qilingan amalni qaytaradi", '<path d="M16 5l4 4-4 4M20 9H10a5.500 5.500 0 0 0 0 11h5"/>'),
    "save": ("word excel ppt paint", "Saqlash", "Faylni saqlaydi", '<path d="M4 4h13l3 3v13H4zM8 4v5h8V4M7 20v-7h10v7"/>'),
    "print": ("word excel ppt", "Chop etish", "Hujjatni printerga yuboradi", '<path d="M7 8V3h10v5M7 17H4V8h16v9h-3M7 13h10v8H7z"/>'),
    "table": ("word ppt", "Jadval qo‘yish", "Hujjatga jadval qo‘yadi", '<rect x="3" y="4" width="18" height="16" rx="1"/><path d="M3 9.300h18M3 14.600h18M9 4v16M15 4v16"/>'),
    "picture": ("word ppt", "Rasm qo‘yish", "Fayldan rasm qo‘yadi", '<rect x="3" y="4" width="18" height="16" rx="1.500"/><circle cx="8.500" cy="9.500" r="1.800"/><path d="M3 18l6-5 4 3 4-5 4 5"/>'),
    "chart": ("word excel ppt", "Diagramma", "Diagramma qo‘yadi", '<path d="M4 3v18h17M8 17v-5M12 17V8M16 17v-8M20 17V6" stroke-width="2.200"/>'),
    "find": ("word excel", "Qidirish", "Hujjatdan matn qidiradi", '<circle cx="10.500" cy="10.500" r="6"/><path d="M15 15l6 6"/>'),
    "autosum": ("excel", "Avtoyig‘indi", "Kataklar yig‘indisini hisoblaydi", '<path d="M18 7V4H6l6 8-6 8h12v-3"/>'),
    "merge": ("excel", "Birlashtirish va o‘rtaga", "Kataklarni birlashtirib, matnni o‘rtaga qo‘yadi", '<rect x="3" y="6" width="18" height="12" rx="1"/><path d="M6 12h4M18 12h-4M8.500 10l2 2-2 2M15.500 10l-2 2 2 2"/>'),
    "sort_asc": ("excel", "O‘sish bo‘yicha saralash", "Ma’lumotni kichikdan kattaga saralaydi", '<path d="M6 4v16M3 17l3 3 3-3M13 6h3M13 11h5M13 16h8"/>'),
    "sort_desc": ("excel", "Kamayish bo‘yicha saralash", "Ma’lumotni kattadan kichikka saralaydi", '<path d="M6 4v16M3 17l3 3 3-3M13 6h8M13 11h5M13 16h3"/>'),
    "filter": ("excel", "Filtr", "Shartga mos qatorlarni ko‘rsatadi", '<path d="M3 4h18l-7 9v7l-4-2v-5z"/>'),
    "percent": ("excel", "Foiz formati", "Katak qiymatini foizda ko‘rsatadi", '<circle cx="7" cy="7" r="2.500"/><circle cx="17" cy="17" r="2.500"/><path d="M18 5L6 19"/>'),
    "wrap": ("excel", "Matnni ko‘chirish", "Katakdagi uzun matnni bir necha qatorga bo‘ladi", '<path d="M4 6h16M4 12h13a3 3 0 0 1 0 6h-4M15 15l-3 3 3 3M4 18h5"/>'),
    "fill_color": ("word excel ppt", "To‘ldirish rangi", "Katak yoki shakl fonini bo‘yaydi", '<path d="M10 4l8 8-7 7-7-7 6-6zM4 12h14M20 15c1 1.500 1.500 2.300 1.500 3a1.500 1.500 0 0 1-3 0c0-.7.500-1.500 1.500-3z"/>'),
    "new_slide": ("ppt", "Yangi slayd", "Taqdimotga yangi slayd qo‘shadi", '<rect x="3" y="5" width="13" height="11" rx="1"/><path d="M19 12v8M15 16h8M6 9h7"/>'),
    "slideshow": ("ppt", "Slaydlarni namoyish qilish", "Taqdimotni to‘liq ekranda boshlaydi", '<rect x="3" y="4" width="18" height="12" rx="1"/><path d="M10 7.500v5l4.500-2.500zM12 16v4M8 20h8"/>'),
    "animation": ("ppt", "Animatsiya", "Obyektga harakat effekti beradi", '<path d="M14 4l2.200 4.600 5 .6-3.700 3.500 1 5-4.500-2.500-4.500 2.500 1-5-3.700-3.500 5-.6zM2 8h3M1 12h3M2 16h3"/>'),
    "transition": ("ppt", "Slayd almashish effekti", "Slaydlar orasidagi o‘tish effektini beradi", '<rect x="3" y="7" width="9" height="10" rx="1"/><path d="M15 7h6v10h-6M8 12h9M14.500 9.500L17 12l-2.500 2.500"/>'),
    "shapes": ("word ppt paint", "Shakllar", "Tayyor shakllarni chizadi", '<rect x="3" y="11" width="9" height="9"/><circle cx="16" cy="15" r="5"/><path d="M10 2l5 7H5z"/>'),
    "textbox": ("word ppt", "Matn maydoni", "Matn yoziladigan maydon qo‘yadi", '<rect x="3" y="5" width="18" height="14" rx="1" stroke-dasharray="3 2"/><path d="M8 9h8M12 9v7"/>'),
    "pencil": ("paint", "Qalam", "Erkin chiziq chizadi", '<path d="M4 20l1-5L16 4l4 4L9 19zM14 6l4 4"/>'),
    "brush": ("paint", "Mo‘yqalam", "Turli qalinlikda bo‘yaydi", '<path d="M20 3c-5 2-9 6-11 10l2 2c4-2 7-6 9-12zM9 14c-3 0-3 3-5 5 3 1 7 0 7-3"/>'),
    "bucket": ("paint", "Rang quyish", "Yopiq sohani rang bilan to‘ldiradi", '<path d="M9 3l9 9-8 7-7-7zM3 12h14M20 14c1.200 1.800 2 2.800 2 4a2 2 0 0 1-4 0c0-1.200.8-2.200 2-4z"/>'),
    "eraser": ("paint", "O‘chirg‘ich", "Chizilganni o‘chiradi", '<path d="M8 20L3 15 14 4l6 6-9 10zM8 10l6 6M7 20h14"/>'),
    "picker": ("paint", "Rang olish", "Rasmdagi rangni tanlab oladi", '<path d="M4 20l1-4 8-8 3 3-8 8zM14 5l2-2c2-1 5 2 4 4l-2 2M12 6l6 6"/>'),
    "zoom": ("paint", "Kattalashtirish", "Rasmni yaqinlashtiradi", '<circle cx="10.500" cy="10.500" r="6.500"/><path d="M15.500 15.500l5.500 5.500M7.500 10.500h6M10.500 7.500v6"/>'),
    "select": ("paint", "Belgilash", "Rasm bo‘lagini belgilaydi", '<rect x="4" y="5" width="16" height="14" stroke-dasharray="3 2.500"/>'),
    "crop": ("paint word ppt", "Kesish", "Rasmning ortiqcha qismini kesadi", '<path d="M7 2v15h15M2 7h15v15"/>'),
    "rotate": ("paint ppt", "Burish", "Rasmni buradi", '<path d="M19 12a7 7 0 1 1-3-5.700M16 2v5h5"/>'),
    "text_tool": ("paint", "Matn yozish", "Rasmga matn qo‘shadi", '<path d="M5 8V4h14v4M12 4v16M9 20h6"/>'),
}


def codes() -> list[str]:
    return [f"{p}.{k}" for k, (progs, *_x) in ICONS.items() for p in progs.split()]


def valid(code) -> bool:
    if not isinstance(code, str):
        return False
    prog, _dot, key = code.partition(".")
    return key in ICONS and prog in ICONS[key][0].split()


def name(code: str) -> str:
    return ICONS[code.partition(".")[2]][1]


def purpose(code: str) -> str:
    return ICONS[code.partition(".")[2]][2]


def program(code: str) -> str:
    return PROGRAMS[code.partition(".")[0]]


def svg(code: str) -> Markup:
    return Markup('<svg class="ui-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.800" stroke-linecap="round" '
                  'stroke-linejoin="round" aria-hidden="true">') + Markup(ICONS[code.partition(".")[2]][3]) + Markup("</svg>")
