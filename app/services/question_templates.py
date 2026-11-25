"""Savol shablonlari: parametrli savollar (sonlari har safar yangi), javobi kod bilan hisoblanadi — AI va token kerak emas.

Har bir shablon: fn(r, daraja) → Made. r — random.Random. Made.key — parametrlar (masalan «45»): «shablon nomi:key»
questions.sig ga yoziladi, shuning uchun bir xil parametrli savol bazada bitta bo'ladi. Javob parametrlardan bir qiymatli
kelib chiqishi shart (variantlar tartibi va chalg'ituvchilar farq qilishi mumkin — bu yangi savol hisoblanmaydi).

Kichik mavzuga shablonlar subtopics.generators ro'yxati orqali bog'lanadi (docs/kontent-formati.md). Bazaga yozish va
tanlash — generator.py. Matnlar o'zbekcha kontent (tarjima qilinmaydi), boshqa savollar kabi.
"""
import math
from dataclasses import dataclass, field

from . import ui_icons

LEVELS = ("easy", "medium", "hard")
CODE_TEXT = "Quyidagi Python kodi natijasini aniqlang:"
SUB = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")


@dataclass(frozen=True)
class Made:
    key: str
    text: str
    answer: dict
    data: dict = field(default_factory=dict)
    why: str | None = None


@dataclass(frozen=True)
class Template:
    name: str
    title: str
    type: str
    levels: tuple[str, ...]
    seconds: int
    fn: object


TEMPLATES: dict[str, Template] = {}


def template(name: str, title: str, type_: str = "single", levels=LEVELS, seconds: int = 60):
    def add(fn):
        TEMPLATES[name] = Template(name, title, type_, tuple(levels), seconds, fn)
        return fn
    return add


# ---------------- Yordamchilar ----------------

def _single(r, key, text, right, wrong, why=None, **data) -> Made:
    """Bitta javobli: to'g'ri javob va 3 ta boshqa-boshqa chalg'ituvchi. Yetmasa, son bo'lsa yaqin sonlar qo'shiladi."""
    right = str(right)
    pool = [w for w in dict.fromkeys(str(x) for x in wrong) if w != right]
    r.shuffle(pool)
    pool = pool[:3]
    step = 1
    while len(pool) < 3 and right.lstrip("-").isdigit():
        for near in (int(right) + step, int(right) - step):
            if near >= 0 and str(near) not in pool and len(pool) < 3:
                pool.append(str(near))
        step += 1
    if len(pool) < 3:
        raise ValueError(f"{key}: chalg'ituvchilar yetmadi")
    opts = [right, *pool]
    r.shuffle(opts)
    return Made(key, text, {"keys": [opts.index(right)]}, {**data, "options": opts}, why)


def _multiple(r, key, text, good, bad, why=None, **data) -> Made:
    opts = [*good, *bad]
    r.shuffle(opts)
    return Made(key, text, {"keys": sorted(opts.index(g) for g in good)}, {**data, "options": opts}, why)


def _matching(r, key, text, pairs, why=None, **data) -> Made:
    """pairs: [(chap, o'ng)], o'ng qiymatlar takrorlanmaydi. O'ng ustun aralashtiriladi."""
    right = [b for _a, b in pairs]
    r.shuffle(right)
    return Made(key, text, {"pairs": [right.index(b) for _a, b in pairs]},
                {**data, "left": [a for a, _b in pairs], "right": right}, why)


def _open(key, text, value, why=None, accept=(), **data) -> Made:
    value = str(value)
    return Made(key, text, {"value": value, **({"accept": list(accept)} if accept else {})},
                {"hint": "Faqat sonni kiriting", **data} if value.isdigit() else data, why)


def _pick(r, level, easy, medium, hard):
    """Darajaga mos oraliqdan butun son."""
    return r.randint(*{"easy": easy, "medium": medium, "hard": hard}[level])


def _base(n: int, base: int) -> str:
    return format(n, {2: "b", 8: "o", 16: "X"}[base]) + str(base).translate(SUB)


def _sample(r, lo, hi, k):
    return sorted(r.sample(range(lo, hi + 1), k))


# ---------------- Sanoq sistemalari ----------------

def _bin_why(n: int) -> str:
    bits = format(n, "b")
    return " + ".join(str(1 << (len(bits) - 1 - i)) for i, b in enumerate(bits) if b == "1") + f" = {n}"


@template("bin_dec", "Ikkilikdan o‘nlikka")
def bin_dec(r, level):
    n = _pick(r, level, (5, 31), (32, 127), (128, 1023))
    return _single(r, str(n), f"{_base(n, 2)} soni o‘nlik sanoq sistemasida nechaga teng?", n,
                   [n + 1, n - 1, n ^ 2, n ^ 4, n + 2], _bin_why(n))


@template("bin_dec_open", "Ikkilikdan o‘nlikka (ochiq)", "open", seconds=90)
def bin_dec_open(r, level):
    n = _pick(r, level, (5, 31), (32, 127), (128, 1023))
    return _open(str(n), f"{_base(n, 2)} sonini o‘nlik sanoq sistemasiga o‘tkazing.", n, _bin_why(n))


@template("dec_bin", "O‘nlikdan ikkilikka")
def dec_bin(r, level):
    n = _pick(r, level, (5, 31), (32, 127), (128, 1023))
    return _single(r, str(n), f"{n} soni ikkilik sanoq sistemasida qanday yoziladi?", _base(n, 2),
                   [_base(x, 2) for x in (n + 1, n - 1, n ^ 2, n ^ 4, n + 2)], _bin_why(n))


@template("bin_add", "Ikkilik sonlarni qo‘shish", seconds=90)
def bin_add(r, level):
    lo, hi = {"easy": (3, 12), "medium": (10, 40), "hard": (40, 200)}[level]
    a, b = r.randint(lo, hi), r.randint(lo, hi)
    s = a + b
    return _single(r, f"{a}+{b}", f"{_base(a, 2)} + {_base(b, 2)} yig‘indisi ikkilik sanoq sistemasida nechaga teng?",
                   _base(s, 2), [_base(x, 2) for x in (s + 1, s - 1, a ^ b, s + 2, a | b)], f"{a} + {b} = {s} = {_base(s, 2)}")


@template("bin_match", "Ikkilik va o‘nlik sonlarni moslash", "matching", seconds=120)
def bin_match(r, level):
    lo, hi = {"easy": (2, 15), "medium": (16, 63), "hard": (64, 255)}[level]
    ns = _sample(r, lo, hi, 4)
    return _matching(r, "-".join(map(str, ns)), "Ikkilik sonlarni o‘nlik qiymati bilan moslashtiring.",
                     [(_base(n, 2), str(n)) for n in ns], "; ".join(f"{_base(n, 2)}: {_bin_why(n)}" for n in ns))


@template("hex_dec", "O‘n oltilikdan o‘nlikka")
def hex_dec(r, level):
    n = _pick(r, level, (17, 63), (64, 255), (256, 1023))
    h = format(n, "X")
    why = " + ".join(f"{int(c, 16)} · {16 ** (len(h) - 1 - i)}" for i, c in enumerate(h)) + f" = {n}"
    return _single(r, str(n), f"{_base(n, 16)} soni o‘nlik sanoq sistemasida nechaga teng?", n,
                   [n + 16, n - 1, n + 1, n - 16 if n > 32 else n + 6, sum(int(c, 16) for c in h)], why)


@template("hex_dec_open", "O‘n oltilikdan o‘nlikka (ochiq)", "open", seconds=90)
def hex_dec_open(r, level):
    n = _pick(r, level, (17, 63), (64, 255), (256, 1023))
    h = format(n, "X")
    why = " + ".join(f"{int(c, 16)} · {16 ** (len(h) - 1 - i)}" for i, c in enumerate(h)) + f" = {n}"
    return _open(str(n), f"{_base(n, 16)} sonini o‘nlik sanoq sistemasida yozing.", n, why)


@template("dec_hex", "O‘nlikdan o‘n oltilikka")
def dec_hex(r, level):
    n = _pick(r, level, (17, 63), (64, 255), (256, 1023))
    return _single(r, str(n), f"{n} soni o‘n oltilik sanoq sistemasida qanday yoziladi?", _base(n, 16),
                   [_base(x, 16) for x in (n + 1, n - 1, n + 16, n ^ 8)], f"{n} = {_base(n, 16)}")


@template("hex_bin", "O‘n oltilikdan ikkilikka", levels=("medium", "hard"))
def hex_bin(r, level):
    n = r.randint(17, 255) if level == "medium" else r.randint(256, 4095)
    return _single(r, str(n), f"{_base(n, 16)} soni ikkilik sanoq sistemasida qanday yoziladi?", _base(n, 2),
                   [_base(x, 2) for x in (n + 1, n - 1, n ^ 16, n ^ 4)],
                   "Har bir o‘n oltilik raqam 4 ta ikkilik raqamga almashtiriladi: "
                   + " ".join(format(int(c, 16), "04b") for c in format(n, "X")))


@template("hex_match", "O‘n oltilik va o‘nlik sonlarni moslash", "matching", seconds=120)
def hex_match(r, level):
    lo, hi = {"easy": (10, 40), "medium": (41, 127), "hard": (128, 255)}[level]
    ns = _sample(r, lo, hi, 4)
    return _matching(r, "-".join(map(str, ns)), "O‘n oltilik sonlarni o‘nlik qiymati bilan moslashtiring.",
                     [(_base(n, 16), str(n)) for n in ns],
                     "; ".join(f"{_base(n, 16)}: {n // 16} · 16 + {n % 16} = {n}" for n in ns))


# ---------------- Axborot hajmi ----------------

@template("bits_alphabet", "Alifbo quvvati", levels=("easy", "medium"))
def bits_alphabet(r, level):
    k, n = r.randint(2, 10), r.choice((10, 20, 30, 40, 50, 60, 80, 100, 120, 150, 200, 250))
    if level == "easy":
        return _single(r, f"1-{k}", f"{2 ** k} ta belgidan iborat alifbodagi bitta belgi necha bit axborot olib keladi?",
                       k, [k + 1, k - 1, 2 * k], f"2^{k} = {2 ** k}, demak bitta belgi {k} bit.")
    return _single(r, f"{n}-{k}", f"{2 ** k} ta belgili alifboda yozilgan {n} ta belgidan iborat matn necha bit axborotga ega?",
                   n * k, [n * (k + 1), n * (k - 1), n * 2 ** k, n + k], f"Bitta belgi {k} bit, {n} · {k} = {n * k} bit.")


@template("text_volume", "Matn hajmi", levels=("medium", "hard"), seconds=90)
def text_volume(r, level):
    pages = r.randint(2, 20) if level == "medium" else r.randint(21, 60)
    lines, chars = r.choice((16, 32, 64)), r.choice((32, 64))
    n = pages * lines * chars
    if n % 1024:                                    # butun Kbayt chiqsin
        pages *= 1024 // math.gcd(n, 1024)
        n = pages * lines * chars
    kb = n // 1024
    return _single(r, f"{pages}x{lines}x{chars}",
                   f"Matn {pages} betdan iborat: har betda {lines} qator, har qatorda {chars} belgi. Har bir belgi 1 bayt bo‘lsa, "
                   "matn hajmi necha Kbayt?", kb, [kb * 2, kb * 8, kb + 1, max(kb // 2, 1) if kb > 2 else kb + 3],
                   f"{pages} · {lines} · {chars} = {n} bayt; {n} ÷ 1024 = {kb} Kbayt.")


@template("unit_convert", "Axborot birliklarini o‘tkazish (ochiq)", "open", seconds=90)
def unit_convert(r, level):
    if level == "easy":
        n = r.randint(2, 99)
        return _open(f"B{n}", f"{n} bayt necha bit?", n * 8, f"{n} · 8 = {n * 8}")
    if level == "medium":
        n = r.randint(2, 64)
        return _open(f"K{n}", f"{n} Kbayt necha bayt?", n * 1024, f"{n} · 1024 = {n * 1024}")
    n = r.randint(1, 32)
    return _open(f"Kb{n}", f"{n} Kbayt necha bit?", n * 8192, f"{n} · 1024 · 8 = {n * 8192}")


@template("unit_match", "Axborot birliklarini moslash", "matching", levels=("easy", "medium"), seconds=120)
def unit_match(r, level):
    ns = _sample(r, 2, 16, 4)
    if level == "easy":
        pairs = [(f"{n} bayt", f"{n * 8} bit") for n in ns]
    else:
        pairs = [(f"{n} Kbayt", f"{n * 1024} bayt") for n in ns]
    return _matching(r, f"{level[0]}{'-'.join(map(str, ns))}", "Teng hajmlarni moslashtiring.", pairs,
                     "1 bayt = 8 bit, shuning uchun bayt soni 8 ga ko‘paytiriladi." if level == "easy"
                     else "1 Kbayt = 1024 bayt, shuning uchun Kbayt soni 1024 ga ko‘paytiriladi.")


# ---------------- Mantiq ----------------

def _logic_exprs():
    return {
        "(A ∧ B) ∨ C": lambda a, b, c: (a and b) or c, "A ∧ (B ∨ C)": lambda a, b, c: a and (b or c),
        "¬A ∨ (B ∧ C)": lambda a, b, c: (not a) or (b and c), "¬(A ∨ B) ∧ C": lambda a, b, c: not (a or b) and c,
        "(A ∨ ¬B) ∧ C": lambda a, b, c: (a or not b) and c, "¬(A ∧ C) ∨ B": lambda a, b, c: not (a and c) or b,
        "A ∧ ¬B ∧ C": lambda a, b, c: a and not b and c, "¬A ∧ (B ∨ ¬C)": lambda a, b, c: (not a) and (b or not c),
        "(A ∨ B) ∧ ¬C": lambda a, b, c: (a or b) and not c, "¬(A ∧ B ∧ C)": lambda a, b, c: not (a and b and c),
        "(A ∧ ¬C) ∨ (B ∧ C)": lambda a, b, c: (a and not c) or (b and c),
        "¬(A ∨ C) ∨ ¬B": lambda a, b, c: not (a or c) or not b}


LOGIC = _logic_exprs()
_BITS = [(a, b, c) for a in (0, 1) for b in (0, 1) for c in (0, 1)]


@template("logic_count", "Mantiqiy ifoda necha holatda rost", levels=("medium", "hard"), seconds=120)
def logic_count(r, level):
    expr = r.choice(list(LOGIC)[:6] if level == "medium" else list(LOGIC)[6:])
    n = sum(bool(LOGIC[expr](*v)) for v in _BITS)
    return _single(r, expr, f"A, B, C ning barcha 8 ta qiymatlar to‘plamidan nechtasida {expr} ifodasi 1 ga teng?",
                   n, [n + 1, n - 1, 8 - n, n + 2],
                   "Ifoda 1 ga teng bo‘ladigan (A, B, C) to‘plamlari: "
                   + ", ".join(f"({a}, {b}, {c})" for a, b, c in _BITS if LOGIC[expr](a, b, c)) + f" — jami {n} ta.")


@template("logic_true", "Rost mantiqiy ifodalar", "multiple", seconds=120)
def logic_true(r, level):
    v = r.choice(_BITS)
    k = {"easy": 4, "medium": 5, "hard": 6}[level]
    for _ in range(50):
        exprs = r.sample(list(LOGIC), k)
        good = [e for e in exprs if LOGIC[e](*v)]
        if 2 <= len(good) < k:
            break
    else:
        raise ValueError("mos ifodalar topilmadi")
    ids = "".join(format(list(LOGIC).index(e), "x") for e in sorted(exprs))
    a, b, c = v
    return _multiple(r, f"{a}{b}{c}-{ids}", f"A = {a}, B = {b}, C = {c} bo‘lsa, qaysi ifodalar 1 ga teng?", good,
                     [e for e in exprs if e not in good],
                     "; ".join(f"{e} = {int(bool(LOGIC[e](*v)))}" for e in exprs))


@template("logic_value", "Mantiqiy ifoda qiymatlari", "matching", levels=("medium", "hard"), seconds=120)
def logic_value(r, level):
    """Ifoda ↔ nechta holatda rost (soni har xil bo'lgan ifodalar)."""
    by_n: dict[int, list[str]] = {}
    for e, f in LOGIC.items():
        by_n.setdefault(sum(bool(f(*v)) for v in _BITS), []).append(e)
    ns = r.sample(sorted(by_n), 3 if level == "medium" else 4)
    pairs = sorted((r.choice(by_n[n]), f"{n} ta") for n in ns)
    ids = "".join(format(list(LOGIC).index(e), "x") for e, _n in pairs)
    return _matching(r, ids, "Ifodani u 1 ga teng bo‘ladigan holatlar soni bilan moslashtiring (A, B, C — 8 ta holat).", pairs,
                     "Har bir ifoda uchun 8 ta holatning rostlik jadvali tuziladi va 1 lar sanaladi: "
                     + "; ".join(f"{e} — {n}" for e, n in pairs))


@template("de_morgan", "De Morgan qonunlari", levels=("easy", "medium"))
def de_morgan(r, level):
    x, y = r.choice((("A", "B"), ("X", "Y"), ("P", "Q"), ("M", "N")))
    op, dual = r.choice((("∧", "∨"), ("∨", "∧")))
    nx, ny = (0, 0) if level == "easy" else r.choice(((1, 0), (0, 1), (1, 1)))
    lit = lambda v, neg: f"¬{v}" if neg else v                      # noqa: E731
    right = f"{lit(x, not nx)} {dual} {lit(y, not ny)}"
    wrong = [f"{lit(x, a)} {o} {lit(y, b)}" for o in (op, dual) for a in (0, 1) for b in (0, 1)]
    return _single(r, f"{x}{op}{y}{nx}{ny}", f"De Morgan qonuniga ko‘ra ¬({lit(x, nx)} {op} {lit(y, ny)}) nimaga teng?",
                   right, wrong, f"Inkor har bir qismga o‘tadi va {op} amali {dual} ga almashadi: {right}.")


# ---------------- Python ----------------

OPS = {">": lambda a, b: a > b, "<": lambda a, b: a < b, ">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b,
       "==": lambda a, b: a == b, "!=": lambda a, b: a != b}


def _cond(r, level, x):
    """(shart matni, rostmi, kalit): oson — taqqoslash, o'rta — qoldiq, qiyin — and/or."""
    if level == "easy":
        op, k = r.choice(list(OPS)), x + r.randint(-3, 3)
        return f"x {op} {k}", OPS[op](x, k)
    if level == "medium":
        m = r.choice((2, 3, 5))
        k = r.randrange(m)
        return f"x % {m} == {k}", x % m == k
    k, m, word = x + r.randint(-4, 4), r.choice((2, 3)), r.choice(("and", "or"))
    a, b = x > k, x % m == 0
    return f"x > {k} {word} x % {m} == 0", (a and b) if word == "and" else (a or b)


def _if_code(r, level):
    """x o'zgaradigan shartli kod: (kalit, kod, natija, boshqa natijalar)."""
    x = _pick(r, level, (2, 12), (6, 30), (10, 50))
    cond, ok = _cond(r, level, x)
    op, k = r.choice(("+", "-", "*")), r.randint(2, 5)
    new = {"+": x + k, "-": x - k, "*": x * k}[op]
    code = f"x = {x}\nif {cond}:\n    x = x {op} {k}\nprint(x)"
    return f"{x}|{cond}|{op}{k}", code, (new if ok else x), [x, new, k, x + k, x * k, x - k, x + 1], cond, ok


@template("py_if", "if operatori: natija")
def py_if(r, level):
    key, code, res, wrong, cond, ok = _if_code(r, level)
    return _single(r, key, CODE_TEXT, res, wrong, f"{cond} — {'rost' if ok else 'yolg‘on'}, natija {res}.", code=code)


@template("py_if_open", "if operatori: natija (ochiq)", "open")
def py_if_open(r, level):
    key, code, res, _wrong, cond, ok = _if_code(r, level)
    return _open(key, "Dastur nechani chiqaradi?", res, f"{cond} — {'rost' if ok else 'yolg‘on'}, natija {res}.", code=code)


@template("py_true", "Rost shartlar", "multiple", seconds=90)
def py_true(r, level):
    x = _pick(r, level, (3, 15), (10, 40), (20, 90))
    for _ in range(50):
        conds = {}
        for _i in range({"easy": 4, "medium": 5, "hard": 5}[level]):
            c, ok = _cond(r, r.choice(("easy", level)), x)
            conds[c] = bool(ok)
        good = [c for c, ok in conds.items() if ok]
        if len(conds) >= 4 and 2 <= len(good) < len(conds):
            break
    else:
        raise ValueError("mos shartlar topilmadi")
    return _multiple(r, f"{x}|{'|'.join(sorted(conds))}", f"x = {x} bo‘lsa, qaysi shartlar True bo‘ladi?", good,
                     [c for c in conds if c not in good],
                     "; ".join(f"{c} — {'True' if ok else 'False'}" for c, ok in conds.items()))


@template("py_ifelse", "if / else: natija")
def py_ifelse(r, level):
    x = _pick(r, level, (2, 12), (6, 30), (10, 50))
    cond, ok = _cond(r, level, x)
    a, b = r.randint(2, 4), r.randint(2, 9)
    res = x * a if ok else x + b
    return _single(r, f"{x}|{cond}|{a}|{b}", CODE_TEXT, res, [x * a, x + b, x, a, b, x - b, x * b],
                   f"{cond} — {'rost' if ok else 'yolg‘on'}, natija {res}.",
                   code=f"x = {x}\nif {cond}:\n    print(x * {a})\nelse:\n    print(x + {b})")


@template("py_ifelse_match", "if / else: qiymatlarni moslash", "matching", seconds=120)
def py_ifelse_match(r, level):
    m, a, b = r.choice((2, 3)), r.randint(2, 5), r.randint(1, 9)
    lo, hi = {"easy": (1, 9), "medium": (5, 20), "hard": (10, 40)}[level]
    f = lambda x: x * a if x % m == 0 else x + b                   # noqa: E731
    for _ in range(50):
        xs = _sample(r, lo, hi, 4)
        if len({f(x) for x in xs}) == 4:
            break
    else:
        raise ValueError("natijalar takrorlandi")
    return _matching(r, f"{m}|{a}|{b}|{'-'.join(map(str, xs))}", "x ning qiymatini dastur natijasi bilan moslashtiring.",
                     [(f"x = {x}", str(f(x))) for x in xs], 
                     f"x {m} ga qoldiqsiz bo‘linsa x * {a}, aks holda x + {b}: "
                     + "; ".join(f"x = {x} → {f(x)}" for x in xs),
                     code=f"if x % {m} == 0:\n    print(x * {a})\nelse:\n    print(x + {b})")


@template("py_elif", "elif zanjiri: natija")
def py_elif(r, level):
    step = {"easy": 10, "medium": 7, "hard": 4}[level]
    lo = r.randint(2, 20)
    mid, hi = lo + step, lo + 2 * step
    x = r.choice((lo - 1, lo, lo + 1, mid, mid + 1, hi, hi + 1, hi + step))
    words = ("Qizil", "Yashil", "Ko‘k", "Sariq")
    op = ">" if level == "easy" else r.choice((">", ">="))
    res = next((w for w, k in zip(words, (hi, mid, lo)) if OPS[op](x, k)), words[3])
    code = (f"x = {x}\nif x {op} {hi}:\n    print('{words[0]}')\nelif x {op} {mid}:\n    print('{words[1]}')\n"
            f"elif x {op} {lo}:\n    print('{words[2]}')\nelse:\n    print('{words[3]}')")
    return _single(r, f"{x}|{op}|{lo}|{step}", CODE_TEXT, res, words,
                   f"Shartlar tartib bilan tekshiriladi, birinchi rost tarmoq bajariladi: {res}.", code=code)


@template("py_elif_match", "elif zanjiri: baholarni moslash", "matching", seconds=120)
def py_elif_match(r, level):
    cut = sorted(r.sample(range(40, 95, 5 if level == "easy" else 1), 3), reverse=True)
    xs = [r.randint(cut[0], 100), r.randint(cut[1], cut[0] - 1), r.randint(cut[2], cut[1] - 1), r.randint(0, cut[2] - 1)]
    pairs = [(f"ball = {x}", g) for x, g in zip(xs, "5432")]
    r.shuffle(pairs)
    code = (f"if ball >= {cut[0]}:\n    print(5)\nelif ball >= {cut[1]}:\n    print(4)\n"
            f"elif ball >= {cut[2]}:\n    print(3)\nelse:\n    print(2)")
    return _matching(r, f"{'-'.join(map(str, cut))}|{'-'.join(map(str, xs))}", "Ballni dastur chiqaradigan baho bilan moslashtiring.",
                     pairs, f"Shartlar yuqoridan pastga tekshiriladi: {cut[0]} dan boshlab 5, {cut[1]} dan 4, {cut[2]} dan 3, qolgani 2.",
                     code=code)


def _range(r, level):
    a = r.randint(0, 5)
    step = 1 if level == "easy" else r.choice((2, 3)) if level == "medium" else r.choice((-1, -2, -3))
    n = r.randint(3, 8)
    if step < 0:
        a = r.randint(8, 20)
    stop = a + step * n
    text = f"range({a}, {stop})" if step == 1 else f"range({a}, {stop}, {step})"
    return text, list(range(a, stop, step))


@template("py_for", "for sikli: yig‘indi")
def py_for(r, level):
    text, xs = _range(r, level)
    s = sum(xs)
    return _single(r, text, CODE_TEXT, s, [s + xs[-1] + (xs[1] - xs[0]), s - xs[-1], s - xs[0], len(xs), s + 1, xs[-1]],
                   " + ".join(map(str, xs)) + f" = {s}", code=f"s = 0\nfor i in {text}:\n    s += i\nprint(s)")


@template("py_for_count", "for sikli: shartli hisob (ochiq)", "open", levels=("medium", "hard"), seconds=90)
def py_for_count(r, level):
    n, m = r.randint(8, 30), r.choice((2, 3, 4, 5))
    if level == "medium":
        res, body, key = sum(1 for i in range(1, n) if i % m == 0), "k += 1", "n"
    else:
        res, body, key = sum(i for i in range(1, n) if i % m == 0), "k += i", "s"
    code = f"k = 0\nfor i in range(1, {n}):\n    if i % {m} == 0:\n        {body}\nprint(k)"
    hits = [str(i) for i in range(1, n) if i % m == 0]
    why = f"range(1, {n}) da {m} ga bo‘linadigan sonlar: {', '.join(hits)} — " + (
        f"{res} ta." if level == "medium" else f"yig‘indisi {res}.")
    return _open(f"{key}{n}-{m}", "Dastur nechani chiqaradi?", res, why, code=code)


@template("py_range", "range() elementlari", "multiple", seconds=90)
def py_range(r, level):
    text, xs = _range(r, level)
    good = r.sample(xs, 2 if level == "easy" else min(3, len(xs)))
    outside = [x for x in range(min(xs) - 2, max(xs) + 4) if x not in xs]
    bad = r.sample(outside, 2)
    key = f"{text}|{'-'.join(map(str, sorted(good + bad)))}"
    return _multiple(r, key, f"Qaysi sonlar {text} ketma-ketligida bor?", [str(x) for x in good], [str(x) for x in bad],
                     f"{text}: " + ", ".join(map(str, xs)))


@template("py_while", "while sikli: natija")
def py_while(r, level):
    if level == "hard":
        n = r.randint(20, 400)
        res, m = 0, n
        while m > 0:
            res, m = res + m % 10, m // 10
        return _single(r, f"raqam{n}", CODE_TEXT, res, [len(str(n)), n, res + 1, res - 1, int(str(n)[::-1])],
                       "Dastur raqamlar yig‘indisini hisoblaydi: " + " + ".join(str(n)[::-1]) + f" = {res}",
                       code=f"n = {n}\ns = 0\nwhile n > 0:\n    s += n % 10\n    n //= 10\nprint(s)")
    x, lim, k = r.randint(1, 6), r.randint(15, 60), r.randint(2, 4)
    op = "+=" if level == "easy" else "*="
    res, n = x, 0
    while res < lim:
        res, n = (res + k if op == "+=" else res * k), n + 1
    return _single(r, f"{x}|{lim}|{op}{k}", CODE_TEXT, res, [lim, res - k, res + k, n, lim - 1, res + 1],
                   f"Sikl {n} marta bajariladi, natija {res}.", code=f"x = {x}\nwhile x < {lim}:\n    x {op} {k}\nprint(x)")


@template("py_rec", "Rekursiya: natija", seconds=90)
def py_rec(r, level):
    if level == "easy":
        n, k = r.randint(4, 20), r.choice((1, 2))
        f = lambda v: 0 if v <= 0 else v + f(v - k)                 # noqa: E731
        body = f"    if n <= 0:\n        return 0\n    return n + f(n - {k})"
    elif level == "medium":
        n, k = r.randint(3, 6), r.randint(1, 3)
        f = lambda v: k if v == 0 else v * f(v - 1)                 # noqa: E731
        body = f"    if n == 0:\n        return {k}\n    return n * f(n - 1)"
    else:
        n, k = r.randint(5, 9), r.randint(1, 4)
        f = lambda v: k if v < 2 else f(v - 1) + f(v - 2)           # noqa: E731
        body = f"    if n < 2:\n        return {k}\n    return f(n - 1) + f(n - 2)"
    res = f(n)
    return _single(r, f"{level[0]}{n}-{k}", CODE_TEXT, res, [f(n - 1), f(n + 1), res + k, res - k, n + k, n * k],
                   "Chaqiruvlar bazaviy shartdan boshlab hisoblanadi: "
                   + ", ".join(f"f({v}) = {f(v)}" for v in sorted({v for v in range(n, -1, -1 if level != "easy" else -k)})),
                   code=f"def f(n):\n{body}\n\nprint(f({n}))")


@template("py_rec_match", "Rekursiya: qiymatlarni moslash", "matching", levels=("medium", "hard"), seconds=150)
def py_rec_match(r, level):
    k, m = r.randint(1, 5), r.choice((2, 3))
    f = lambda v: k if v == 0 else m * f(v - 1) + (1 if level == "hard" else 0)     # noqa: E731
    ns = _sample(r, 0, 5, 4)
    tail = " + 1" if level == "hard" else ""
    return _matching(r, f"{level[0]}{k}-{m}-{''.join(map(str, ns))}", "Chaqiruvni natijasi bilan moslashtiring.",
                     [(f"f({n})", str(f(n))) for n in ns],
                     ", ".join(f"f({v}) = {f(v)}" for v in range(max(ns) + 1)),
                     code=f"def f(n):\n    if n == 0:\n        return {k}\n    return {m} * f(n - 1){tail}")


# ---------------- Algoritmlar ----------------

@template("bsearch_steps", "Ikkilik qidiruv qadamlari")
def bsearch_steps(r, level):
    n = _pick(r, level, (4, 31), (32, 255), (256, 5000))
    k = n.bit_length()
    return _single(r, str(n), f"{n} ta elementli saralangan massivda ikkilik qidiruv eng ko‘pi bilan necha qadamda tugaydi?",
                   k, [k + 1, k - 1, n // 2, n, k + 2], f"Har qadamda oraliq ikkiga bo‘linadi: 2^{k} = {2 ** k} > {n}.")


@template("bsearch_mid", "Ikkilik qidiruv: birinchi solishtirish")
def bsearch_mid(r, level):
    n = {"easy": 5, "medium": 7, "hard": 9}[level]
    xs = _sample(r, 1, 60, n)
    mid = xs[(n - 1) // 2]
    return _single(r, "-".join(map(str, xs)), f"Saralangan massiv: {xs}. Ikkilik qidiruv avval qaysi elementni tekshiradi?",
                   mid, [xs[0], xs[-1], xs[(n - 1) // 2 + 1], xs[(n - 1) // 2 - 1]],
                   f"O‘rtadagi element: indeks (0 + {n - 1}) // 2 = {(n - 1) // 2}, qiymati {mid}.")


@template("search_true", "Qidiruv haqida to‘g‘ri fikrlar", "multiple", seconds=90)
def search_true(r, level):
    n = _pick(r, level, (12, 60), (61, 500), (501, 4000))
    k = n.bit_length()
    good = [f"Ketma-ket qidiruv eng yomon holda {n} ta elementni tekshiradi", f"Ikkilik qidiruv eng yomon holda {k} qadam bajaradi"]
    bad = [f"Ikkilik qidiruv eng yomon holda {n // 2} qadam bajaradi", f"Ketma-ket qidiruv eng yomon holda {k} ta elementni tekshiradi"]
    return _multiple(r, str(n), f"{n} ta elementli saralangan massiv uchun qaysi fikrlar to‘g‘ri?", good, bad,
                     f"2^{k} = {2 ** k} > {n}, shuning uchun ikkilik qidiruvga {k} qadam yetadi.")


# ---------------- Elektron jadval ----------------

def _sheet(cols: dict[str, list[int]], target: str) -> dict:
    n = len(next(iter(cols.values())))
    head = ["", *cols, "C"]
    rows = [[str(i + 1), *(str(c[i]) for c in cols.values()), ""] for i in range(n)]
    rows.append([str(n + 1), *("" for _ in cols), "?"])
    assert target == f"C{n + 1}"
    return {"head": head, "rows": rows}


@template("xl_sumif", "SUMIF formulasi", seconds=90)
def xl_sumif(r, level):
    n = {"easy": 3, "medium": 4, "hard": 5}[level]
    a, b = [r.randint(1, 9) for _ in range(n)], [r.randint(1, 20) * (10 if level == "easy" else 5) for _ in range(n)]
    op, k = r.choice((">", "<", ">=", "<=")), r.choice(a)
    s = sum(y for x, y in zip(a, b) if OPS[op](x, k))
    rest = sum(b) - s
    return _single(r, f"{a}{b}{op}{k}".replace(" ", ""), f'Jadvalda C{n + 1} katakka =SUMIF(A1:A{n};"{op}{k}";B1:B{n}) formulasi yozildi. '
                   f"C{n + 1} qiymati nechaga teng?", s, [sum(b), rest, sum(a), s + b[0], s + 5, s + 10],
                   f"A ustunda shartga ({op}{k}) mos qatorlarning B qiymatlari qo‘shiladi: "
                   + (" + ".join(str(y) for x, y in zip(a, b) if OPS[op](x, k)) or "mos qator yo‘q") + (f" = {s}" if s else "; natija 0"),
                   table=_sheet({"A": a, "B": b}, f"C{n + 1}"))


@template("xl_countif", "COUNTIF formulasi")
def xl_countif(r, level):
    n = {"easy": 4, "medium": 5, "hard": 6}[level]
    a, b = [r.randint(1, 20) for _ in range(n)], [r.randint(1, 20) for _ in range(n)]
    op, k = r.choice((">", "<", ">=", "<=")), r.choice(a)
    c = sum(1 for x in a if OPS[op](x, k))
    return _single(r, f"{a}{op}{k}".replace(" ", ""), f'Jadvalda C{n + 1} katakka =COUNTIF(A1:A{n};"{op}{k}") formulasi yozildi. '
                   f"C{n + 1} qiymati nechaga teng?", c, [n - c, n, c + 1, c - 1, k],
                   f"Shartga ({op}{k}) mos kataklar: " + (", ".join(str(x) for x in a if OPS[op](x, k)) or "yo‘q") + f" — {c} ta.",
                   table=_sheet({"A": a, "B": b}, f"C{n + 1}"))


@template("xl_match", "Formulalarni natijasi bilan moslash", "matching", seconds=150)
def xl_match(r, level):
    n = {"easy": 3, "medium": 4, "hard": 5}[level]
    for _ in range(80):
        a = [r.randint(1, 20) for _ in range(n)]
        k = r.choice(a)
        vals = {"SUM": sum(a), "MAX": max(a), "MIN": min(a), "COUNT": n}
        pairs = [(f"={f}(A1:A{n})", str(v)) for f, v in vals.items()]
        pairs.append((f'=SUMIF(A1:A{n};">{k}")', str(sum(x for x in a if x > k))))
        if len({v for _f, v in pairs}) == len(pairs):
            break
    else:
        raise ValueError("natijalar takrorlandi")
    return _matching(r, f"{a}{k}".replace(" ", ""), "Formulalarni natijasi bilan moslashtiring.", pairs,
                     "SUM — yig‘indi, MAX — eng katta, MIN — eng kichik, COUNT — sonli kataklar soni, SUMIF — shartga mos kataklar yig‘indisi.",
                     table={"head": ["", "A"], "rows": [[str(i + 1), str(x)] for i, x in enumerate(a)]})


# ---------------- Elektron jadval oynasi (data.sheet) ----------------

def _grid(rows, active, formula) -> dict:
    return {"rows": [[str(c) for c in r] for r in rows], "active": active, "formula": formula}


@template("xl_ref", "Formuladagi katak havolalari", seconds=90)
def xl_ref(r, level):
    a, b, c = (r.randint(2, 9) for _ in range(3))
    f, v = {"easy": (("=A1+B1*C1", a + b * c),), "medium": (("=(A1+B1)*C1", (a + b) * c), ("=A1*B1-C1", a * b - c)),
            "hard": (("=A1^2+B1*C1", a * a + b * c), ("=SUM(A1:C1)*2", (a + b + c) * 2), ("=MAX(A1:C1)-MIN(A1:C1)", max(a, b, c) - min(a, b, c)))}[level][
        r.randrange({"easy": 1, "medium": 2, "hard": 3}[level])]
    return _single(r, f"{f}|{a}-{b}-{c}", "D1 katakdagi formula natijasi nechaga teng?", v,
                   [a + b + c, (a + b) * c, a + b * c, a * b * c, v + 1, v + 2], f"A1 = {a}, B1 = {b}, C1 = {c}: {f} → {v}.",
                   sheet=_grid([[a, b, c, "?"]], "D1", f))


@template("xl_abs", "Formulani nusxalash: nisbiy va mutlaq havola", seconds=90)
def xl_abs(r, level):
    col, row, to_row = r.choice("CD"), r.randint(1, 4), r.randint(5, 9)
    d = to_row - row
    one = f"$A${row}" if level != "easy" else f"A{row}"
    two = f"B{row}" if level != "hard" else f"B${row}"
    moved = {"easy": (f"A{to_row}", f"B{to_row}"), "medium": (f"$A${row}", f"B{to_row}"), "hard": (f"$A${row}", f"B${row}")}[level]
    op = r.choice("+*-")
    right = f"={moved[0]}{op}{moved[1]}"
    wrong = [f"=A{to_row}{op}B{to_row}", f"=$A${to_row}{op}B{to_row}", f"={one}{op}{two}", f"=$A${row}{op}B{to_row}", f"=A{row}{op}B{to_row}",
             f"=$A${to_row}{op}$B${to_row}"]
    return _single(r, f"{col}{row}>{to_row}{op}{level[0]}", f"{col}{row} katakdagi ={one}{op}{two} formulasi {col}{to_row} katakka nusxalandi. "
                   f"{col}{to_row} da qanday formula hosil bo‘ladi?", right, wrong,
                   f"Nusxa {d} qator pastga: «$» belgisi yo‘q qator raqami {d} ga oshadi, «$» bilan yozilgani o‘zgarmaydi.", option_view="code")


@template("xl_if", "IF formulasi", seconds=60)
def xl_if(r, level):
    a, k, op = r.randint(1, 20), r.randint(1, 20), r.choice((">", "<", ">=", "<="))
    ok = OPS[op](a, k)
    if level == "easy":
        yes, no, f = "Ha", "Yo‘q", f'=IF(A1{op}{k};"Ha";"Yo‘q")'
    else:
        m, n = r.randint(2, 4), r.randint(5, 9)
        yes, no, f = str(a * m), str(a + n), f"=IF(A1{op}{k};A1*{m};A1+{n})"
    right = yes if ok else no
    return _single(r, f"{f}|{a}", "B1 katakda nima chiqadi?", right, [no if ok else yes, str(a), "Xato", "0", "ROST"],
                   f"A1 = {a}: {a} {op} {k} — {'rost' if ok else 'yolg‘on'}.", sheet=_grid([[a, "?"]], "B1", f))


# ---------------- JavaScript ----------------

JS_TEXT = "Quyidagi JavaScript kodi natijasini aniqlang:"


@template("js_loop", "JavaScript: for sikli")
def js_loop(r, level):
    a, b = r.randint(1, 4), r.randint(5, 9)
    step = {"easy": 1, "medium": 2, "hard": 3}[level]
    xs = list(range(a, b + 1, step))
    total = sum(xs)
    inc = "i++" if step == 1 else f"i += {step}"
    return _single(r, f"{a}-{b}-{step}", JS_TEXT, total, [total + b, total - a, len(xs), sum(range(a, b)), total + 1],
                   " + ".join(map(str, xs)) + f" = {total}", lang="javascript",
                   code=f"let s = 0;\nfor (let i = {a}; i <= {b}; {inc}) {{\n  s += i;\n}}\nconsole.log(s);")


@template("js_concat", "JavaScript: qator va son qo‘shish")
def js_concat(r, level):
    a, b, c = r.randint(1, 9), r.randint(1, 9), r.randint(1, 9)
    expr, res, why = {
        "easy": (f'"{a}" + {b}', f"{a}{b}", "Qatorga son qo‘shilsa, son qatorga aylanadi va yoniga yoziladi."),
        "medium": (f'{a} + {b} + "{c}"', f"{a + b}{c}", "Amallar chapdan o‘ngga: avval sonlar qo‘shiladi, keyin natija qatorga ulanadi."),
        "hard": (f'"{a}" * {b} + {c}', f"{a * b + c}", "«*» amali qatorni songa aylantiradi, keyin sonlar qo‘shiladi.")}[level]
    return _single(r, expr, JS_TEXT, res, [str(a + b + c), f"{a}{b}{c}", str(a + b), f"{a}{b}", str(a * b), f"{a + b}{c}", "NaN", "undefined"], why,
                   lang="javascript", code=f"console.log({expr});")


@template("js_if", "JavaScript: shart")
def js_if(r, level):
    x, k, op = r.randint(1, 20), r.randint(1, 20), r.choice((">", "<", ">=", "<="))
    ok, a, b = OPS[op](x, k), r.randint(2, 5), r.randint(1, 9)
    res = x * a if ok else x - b
    tail = f"x *= {a};" if level == "easy" else f"x = x * {a};"
    return _single(r, f"{x}{op}{k}|{a}|{b}", JS_TEXT, res, [x, x * a, x - b, x + b, a, b], f"{x} {op} {k} — {'rost' if ok else 'yolg‘on'}, natija {res}.",
                   lang="javascript", code=f"let x = {x};\nif (x {op} {k}) {{\n  {tail}\n}} else {{\n  x -= {b};\n}}\nconsole.log(x);")


@template("js_match", "JavaScript: ifodalarni natijasi bilan moslash", "matching", levels=("medium", "hard"), seconds=120)
def js_match(r, level):
    for _ in range(60):
        a, b = r.randint(2, 9), r.randint(2, 9)
        pairs = [(f"{a} + {b}", str(a + b)), (f'"{a}" + {b}', f"{a}{b}"), (f'"{a}" * "{b}"', str(a * b)), (f"{a} % {b}", str(a % b))]
        if level == "hard":
            pairs.append((f'typeof "{a}"', "string"))
        if len({v for _e, v in pairs}) == len(pairs):
            break
    else:
        raise ValueError("natijalar takrorlandi")
    return _matching(r, f"{level[0]}{a}-{b}", "JavaScript ifodalarini natijasi bilan moslashtiring.", pairs,
                     "«+» qator bilan ishlasa ulaydi, «*» va «%» sonlar ustida bajariladi.")


# ---------------- HTML va CSS ----------------

HTML_TAGS = {"<h1>": "eng katta sarlavha", "<p>": "abzas", "<a>": "havola", "<img>": "rasm", "<ul>": "belgili ro‘yxat", "<ol>": "raqamlangan ro‘yxat",
             "<li>": "ro‘yxat elementi", "<table>": "jadval", "<tr>": "jadval qatori", "<td>": "jadval katagi", "<br>": "yangi qatorga o‘tish",
             "<hr>": "gorizontal chiziq", "<form>": "forma", "<input>": "kiritish maydoni", "<title>": "brauzer yorlig‘idagi sarlavha",
             "<strong>": "muhim (qalin) matn", "<em>": "urg‘uli (kursiv) matn"}
CSS_PROPS = {"color": "matn rangi", "background-color": "fon rangi", "font-size": "shrift o‘lchami", "font-weight": "shrift qalinligi",
             "text-align": "matnni tekislash", "margin": "tashqi bo‘shliq", "padding": "ichki bo‘shliq", "border": "chegara chizig‘i",
             "width": "element kengligi", "border-radius": "burchaklarni yumaloqlash", "text-decoration": "matn chizig‘i (masalan, tagiga chiziq)",
             "line-height": "qatorlar balandligi", "letter-spacing": "harflar orasidagi masofa", "display": "elementning joylashish turi"}


def _fact(r, level, facts: dict, ask_name: str, ask_use: str, view: str | None = None):
    """Nomi → vazifasi yoki vazifasi → nomi."""
    name = r.choice(list(facts))
    others = r.sample([k for k in facts if k != name], 5)
    extra = {"option_view": view} if view else {}
    if r.random() < 0.5 if level == "medium" else level == "easy":
        return _single(r, f"n:{name}", ask_use.format(facts[name]), name, others, f"{name} — {facts[name]}.", **extra)
    return _single(r, f"v:{name}", ask_name.format(name), facts[name], [facts[k] for k in others], f"{name} — {facts[name]}.")


def _fact_match(r, level, facts: dict, text: str):
    names = sorted(r.sample(list(facts), {"easy": 3, "medium": 4, "hard": 5}[level]))
    return _matching(r, "|".join(names), text, [(n, facts[n]) for n in names], "; ".join(f"{n} — {facts[n]}" for n in names) + ".")


@template("html_tag", "HTML teglari")
def html_tag(r, level):
    return _fact(r, level, HTML_TAGS, "HTML’da {} tegi nima uchun ishlatiladi?", "HTML’da «{}» uchun qaysi teg ishlatiladi?", "code")


@template("html_match", "HTML teglarini moslash", "matching", seconds=120)
def html_match(r, level):
    return _fact_match(r, level, HTML_TAGS, "HTML teglarini vazifasi bilan moslashtiring.")


@template("css_prop", "CSS xossalari")
def css_prop(r, level):
    return _fact(r, level, CSS_PROPS, "CSS’da {} xossasi nimani belgilaydi?", "CSS’da «{}» qaysi xossa bilan belgilanadi?", "code")


@template("css_match", "CSS xossalarini moslash", "matching", seconds=120)
def css_match(r, level):
    return _fact_match(r, level, CSS_PROPS, "CSS xossalarini vazifasi bilan moslashtiring.")


# ---------------- LOGO ----------------

POLYGONS = {3: "Muntazam uchburchak", 4: "Kvadrat", 5: "Muntazam beshburchak", 6: "Muntazam oltiburchak", 8: "Muntazam sakkizburchak",
            9: "Muntazam to‘qqizburchak", 10: "Muntazam o‘nburchak", 12: "Muntazam o‘n ikki burchak"}


def _poly(n: int, a: int) -> str:
    return f"repeat {n} [fd {a} rt {360 // n}]"


@template("logo_figure", "LOGO: shaklni aniqlash")
def logo_figure(r, level):
    n, a = r.choice({"easy": (3, 4, 6), "medium": (3, 5, 6, 8), "hard": (5, 8, 9, 10, 12)}[level]), r.randrange(20, 101, 5)
    return _single(r, f"{n}-{a}", "LOGO buyruqlari bajarilganda qanday shakl chiziladi?", POLYGONS[n], [v for k, v in POLYGONS.items() if k != n],
                   f"Burilish burchagi {360 // n}°, 360 ÷ {360 // n} = {n} tomon.", logo={"src": _poly(n, a), "show": "code"})


@template("logo_pick", "LOGO: chizmani tanlash", seconds=90)
def logo_pick(r, level):
    pool = {"easy": (3, 4, 6, 8), "medium": (3, 4, 5, 6, 8), "hard": (5, 6, 8, 9, 10)}[level]
    n, a = r.choice(pool), r.randrange(20, 101, 5)
    others = r.sample([k for k in pool if k != n], 3)
    return _single(r, f"{n}-{a}", f"«{_poly(n, a)}» buyrug‘i bilan qaysi shakl chiziladi?", _poly(n, a), [_poly(k, a) for k in others],
                   f"360 ÷ {360 // n} = {n} tomonli muntazam ko‘pburchak.", option_view="logo")


@template("logo_perimeter", "LOGO: toshbaqa bosib o‘tgan yo‘l (ochiq)", "open", seconds=90)
def logo_perimeter(r, level):
    if level == "easy":
        n, a = r.choice((3, 4, 5, 6)), r.randrange(10, 101, 5)
        src, v, why = _poly(n, a), n * a, f"{n} · {a} = {n * a}"
    else:
        n, a, b = r.choice((2, 3, 4, 5)), r.randrange(10, 61, 5), r.randrange(5, 41, 5)
        src, v, why = f"repeat {n} [fd {a} bk {b} rt 90]", n * (a + b), f"Har takrorda {a} + {b} qadam: {n} · {a + b} = {n * (a + b)}"
    return _open(src, "Toshbaqa jami necha qadam yo‘l bosadi (orqaga yurgani ham qo‘shiladi)?", v, why, logo={"src": src, "show": "code"})


LOGO_WORDS = {"fd 50": "50 qadam oldinga", "bk 50": "50 qadam orqaga", "rt 90": "90° o‘ngga burilish", "lt 90": "90° chapga burilish",
              "pu": "qalamni ko‘tarish", "pd": "qalamni tushirish", "home": "boshlang‘ich nuqtaga qaytish", "cs": "ekranni tozalash",
              "repeat 4 [ ]": "4 marta takrorlash"}


@template("logo_match", "LOGO buyruqlarini moslash", "matching", seconds=120)
def logo_match(r, level):
    return _fact_match(r, level, LOGO_WORDS, "LOGO buyruqlarini ma’nosi bilan moslashtiring.")


# ---------------- Scratch ----------------

@template("scratch_sum", "Scratch: o‘zgaruvchi qiymati", seconds=90)
def scratch_sum(r, level):
    x, n, k = r.randint(0, 9), r.randint(2, 6), r.randint(1, 5)
    lines = ["voqea: bayroq bosilganda", f"o‘zgaruvchi: [x] ni [{x}] ga o‘rnat", f"boshqaruv: [{n}] marta takrorla", f"  o‘zgaruvchi: [x] ni [{k}] ga o‘zgartir"]
    v = x + n * k
    why = f"{x} + {n} · {k} = {v}"
    if level == "hard":
        m = r.randint(2, 3)
        lines.append(f"  o‘zgaruvchi: [x] ni [{m}] ga o‘zgartir")
        v, why = x + n * (k + m), f"{x} + {n} · ({k} + {m}) = {x + n * (k + m)}"
    elif level == "medium":
        m = r.randint(1, 4)
        lines.append(f"o‘zgaruvchi: [x] ni [-{m}] ga o‘zgartir")
        v, why = v - m, f"{x} + {n} · {k} − {m} = {v - m}"
    lines.append("ko‘rinish: (x) de")
    return _single(r, "|".join(lines[1:-1]).replace("o‘zgaruvchi: ", "").replace("boshqaruv: ", ""), "Qahramon nechani aytadi?", v,
                   [x + k, n * k, v + k, v - k, x + n, v + 1], why, scratch="\n".join(lines))


@template("scratch_steps", "Scratch: qadamlar soni")
def scratch_steps(r, level):
    n, d = r.randint(2, 10), r.choice((5, 10, 15, 20))
    lines = ["voqea: bayroq bosilganda", f"boshqaruv: [{n}] marta takrorla", f"  harakat: [{d}] qadam yur"]
    v, why = n * d, f"{n} · {d} = {n * d}"
    if level != "easy":
        e = r.choice((5, 10, 25))
        lines += [f"harakat: [{e}] qadam yur"]
        v, why = n * d + e, f"{n} · {d} + {e} = {n * d + e}"
    if level == "hard":
        m = r.randint(2, 3)
        lines = [lines[0], f"boshqaruv: [{m}] marta takrorla", f"  boshqaruv: [{n}] marta takrorla", f"    harakat: [{d}] qadam yur"]
        v, why = m * n * d, f"{m} · {n} · {d} = {m * n * d}"
    return _single(r, f"{level[0]}{n}-{d}-{v}", "Qahramon jami necha qadam yuradi?", v, [n + d, n * d, d, v + d, v - d, v * 2], why,
                   scratch="\n".join(lines))


@template("scratch_if", "Scratch: shart", seconds=90)
def scratch_if(r, level):
    x, k, op = r.randint(1, 15), r.randint(1, 15), r.choice((">", "<"))
    ok = OPS[op](x, k)
    words = ("Salom", "Rahmat")
    lines = ["voqea: bayroq bosilganda", f"o‘zgaruvchi: [x] ni [{x}] ga o‘rnat", f"boshqaruv: agar <x {op} {k}> bo‘lsa", f"  ko‘rinish: [{words[0]}] de",
             "boshqaruv: aks holda", f"  ko‘rinish: [{words[1]}] de"]
    return _single(r, f"{x}{op}{k}", "Qahramon nima deydi?", words[0] if ok else words[1],
                   [words[1] if ok else words[0], "Hech narsa", "Ikkalasini ham", str(x)], f"{x} {op} {k} — {'rost' if ok else 'yolg‘on'}.",
                   scratch="\n".join(lines))


SCRATCH_GROUPS = {"Harakat": ("10 qadam yur", "o‘ngga 15° bur", "x: 0 y: 0 ga o‘t"), "Ko‘rinish": ("Salom! de", "keyingi libos", "o‘lchamni 10 ga o‘zgartir"),
                  "Ovoz": ("Miyov ovozini ijro et", "ovoz balandligini 50% qil"), "Voqealar": ("bayroq bosilganda", "bo‘sh joy tugmasi bosilganda"),
                  "Boshqaruv": ("1 soniya kut", "10 marta takrorla", "agar … bo‘lsa"), "Sensorlar": ("sichqonchaga tegdimi?", "ismingiz nima? so‘ra"),
                  "Amallar": ("( ) + ( )", "1 dan 10 gacha tasodifiy son")}


@template("scratch_match", "Scratch bloklarini bo‘limi bilan moslash", "matching", seconds=120)
def scratch_match(r, level):
    groups = sorted(r.sample(list(SCRATCH_GROUPS), {"easy": 3, "medium": 4, "hard": 5}[level]))
    pairs = [(r.choice(SCRATCH_GROUPS[g]), g) for g in groups]
    ids = "-".join(f"{g[:3]}{SCRATCH_GROUPS[g].index(b)}" for b, g in pairs)
    return _matching(r, ids, "Scratch bloklarini bo‘limi bilan moslashtiring.", pairs,
                     "; ".join(f"«{b}» — {g}" for b, g in pairs) + ".")


# ---------------- Word, Excel, PowerPoint, Paint tugmalari ----------------

def _program(prog: str, title: str):
    codes = [c for c in ui_icons.codes() if c.startswith(prog + ".")]

    def icon(r, level):
        c = r.choice(codes)
        use = level != "easy"
        label = ui_icons.purpose if use else ui_icons.name
        others = {label(x) for x in codes if x != c and label(x) != label(c)}
        return _single(r, f"{c}-{int(use)}", f"{title} dasturidagi bu tugma nima uchun xizmat qiladi?" if use else f"{title} dasturidagi bu tugma qanday ataladi?",
                       label(c), r.sample(sorted(others), 5), f"Bu — «{ui_icons.name(c)}» tugmasi. {ui_icons.purpose(c)}.", ui=[c])

    def pick(r, level):
        c = r.choice(codes)
        others = [x for x in codes if ui_icons.name(x) != ui_icons.name(c)]
        ask = f"«{ui_icons.name(c)}» tugmasini toping." if level == "easy" else f"Qaysi tugma quyidagi amalni bajaradi: {ui_icons.purpose(c)[0].lower()}{ui_icons.purpose(c)[1:]}?"
        return _single(r, f"{c}-{level[0] == 'e'}", f"{title}: {ask}", c, r.sample(others, 3), f"{ui_icons.name(c)}: {ui_icons.purpose(c)}.", option_view="ui")

    def match(r, level):
        chosen = sorted(r.sample(codes, {"easy": 3, "medium": 4, "hard": 5}[level]))
        return _matching(r, "|".join(c.split(".")[1] for c in chosen), f"{title} tugmalarini vazifasi bilan moslashtiring.",
                         [(ui_icons.name(c), ui_icons.purpose(c)) for c in chosen],
                         "; ".join(f"{ui_icons.name(c)} — {ui_icons.purpose(c)}" for c in chosen) + ".")

    template(f"{prog}_icon", f"{title}: tugma vazifasi")(icon)
    template(f"{prog}_pick", f"{title}: tugmani topish")(pick)
    template(f"{prog}_match", f"{title}: tugmalarni moslash", "matching", seconds=120)(match)


for _p, _t in ui_icons.PROGRAMS.items():
    _program(_p, _t)
