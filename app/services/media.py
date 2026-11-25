"""Savol formatlari: dastur oynasi, kod va chizmalar — rasm emas, ixcham tavsif (data) saqlanadi, server HTML/SVG chizadi.

| data maydoni | Nima                                                             | Misol                                              |
|--------------|------------------------------------------------------------------|----------------------------------------------------|
| code, lang   | Kod (til: highlight.LANGS; standart python)                       | {"code": "let x = 5", "lang": "javascript"}        |
| html, show   | HTML/CSS natijasi: show = code / result / both; html — CSS uchun   | {"code": "p{color:red}", "lang": "css", "html": …} |
| sheet        | Excel oynasi: kataklar, faol katak, formula qatori                | {"rows": [["1", "2"]], "active": "C1", "formula"}  |
| scratch      | Scratch bloklari: «kategoriya: matn», ichkari — 2 bo'sh joy        | "voqea: bayroq bosilganda\\nboshqaruv: [4] marta"   |
| logo         | LOGO: {"src": buyruqlar, "show": drawing / code / both}           | {"src": "repeat 4 [fd 50 rt 90]", "show": "both"}  |
| ui           | Dastur tugmalari (ui_icons): ["word.bold", …]                      |                                                    |
| option_view  | Variantlar ko'rinishi: code, logo (chizma) yoki ui (tugma)         | variant matni — kod, LOGO buyrug'i yoki tugma kodi |

Serverda chiziladi: pleyer, attestatsiya oynasi, natija, AI tutor va oflayn sahifada bir xil, brauzerga kutubxona kerak emas.
Hamma matn ekranlanadi. HTML natijasi skriptsiz (sandbox) oynada. Tekshiruv — check().
"""
import math
import re

from flask_babel import gettext as _
from markupsafe import Markup, escape

from . import ui_icons
from .highlight import LANGS, highlight, norm_lang

KEYS = ("code", "lang", "html", "show", "sheet", "scratch", "logo", "ui")
SHOWS = ("code", "result", "both")
LOGO_SHOWS = ("drawing", "code", "both")
OPTION_VIEWS = ("code", "logo", "ui")
CODE_MAX, HTML_MAX, SCRATCH_LINES, LOGO_STEPS, SHEET_ROWS, SHEET_COLS = 5000, 3000, 60, 3000, 20, 12

CATEGORIES = {"voqea": "ev", "harakat": "mo", "ko‘rinish": "lo", "ovoz": "so", "boshqaruv": "co", "sensor": "se", "amal": "op",
              "o‘zgaruvchi": "va", "qalam": "pe", "blok": "my"}
_APOS = str.maketrans({"'": "‘", "ʻ": "‘", "’": "‘", "`": "‘"})


# ---------------- Tekshiruv ----------------

def check(data: dict, qtype: str | None = None) -> list[str]:
    """Formatlar to'g'riligi; xatolar ro'yxati."""
    errs = []
    code, lang = data.get("code"), data.get("lang")
    if code is not None and (not isinstance(code, str) or len(code) > CODE_MAX):
        errs.append(f"data.code: {CODE_MAX} belgigacha matn")
    if lang is not None and lang not in LANGS:
        errs.append(f"data.lang: {', '.join(LANGS)} dan biri")
    if data.get("show") is not None and data["show"] not in SHOWS:
        errs.append(f"data.show: {', '.join(SHOWS)} dan biri")
    if data.get("show") in ("result", "both") and lang not in ("html", "css"):
        errs.append("data.show: natija faqat html va css uchun")
    if data.get("html") is not None and (not isinstance(data["html"], str) or len(data["html"]) > HTML_MAX):
        errs.append(f"data.html: {HTML_MAX} belgigacha matn")
    if data.get("sheet") is not None:
        errs += _check_sheet(data["sheet"])
    if data.get("scratch") is not None:
        errs += _check_scratch(data["scratch"])
    if data.get("logo") is not None:
        logo = data["logo"]
        if not isinstance(logo, dict) or logo.get("show", "both") not in LOGO_SHOWS:
            errs.append(f"data.logo: {{src, show}}, show — {', '.join(LOGO_SHOWS)} dan biri")
        else:
            errs += [f"data.logo: {e}" for e in _logo_errors(logo.get("src"))]
    ui = data.get("ui")
    if ui is not None and (not isinstance(ui, list) or not 1 <= len(ui) <= 12 or not all(ui_icons.valid(c) for c in ui)):
        errs.append("data.ui: 1–12 ta tugma kodi (masalan word.bold)")
    view = data.get("option_view")
    if view is not None:
        opts = data.get("options") or []
        if view not in OPTION_VIEWS or qtype not in (None, "single", "multiple"):
            errs.append(f"data.option_view: {', '.join(OPTION_VIEWS)} dan biri (faqat variantli savolda)")
        elif view == "ui" and not all(ui_icons.valid(o) for o in opts):
            errs.append("data.options: har biri tugma kodi bo'lsin (masalan word.bold)")
        elif view == "logo":
            errs += [f"data.options[{n}]: {e}" for n, o in enumerate(opts) for e in _logo_errors(o)]
    return errs


def _check_sheet(s) -> list[str]:
    rows = s.get("rows") if isinstance(s, dict) else None
    if not isinstance(rows, list) or not 1 <= len(rows) <= SHEET_ROWS or not all(
            isinstance(r, list) and 1 <= len(r) <= SHEET_COLS and all(isinstance(c, str) and len(c) <= 100 for c in r) for r in rows):
        return [f"data.sheet.rows: {SHEET_ROWS} qator × {SHEET_COLS} ustungacha matnli kataklar"]
    errs = []
    if s.get("active") is not None and not (isinstance(s["active"], str) and re.fullmatch(r"[A-L](?:[1-9]|1\d|20)", s["active"])):
        errs.append("data.sheet.active: katak manzili (masalan C4)")
    if s.get("formula") is not None and (not isinstance(s["formula"], str) or len(s["formula"]) > 200):
        errs.append("data.sheet.formula: 200 belgigacha matn")
    return errs


def _check_scratch(src) -> list[str]:
    if not isinstance(src, str) or not src.strip() or len(src) > 4000 or src.count("\n") >= SCRATCH_LINES:
        return [f"data.scratch: {SCRATCH_LINES} qatorgacha matn"]
    try:
        _scratch_tree(src)
    except ValueError as e:
        return [f"data.scratch: {e}"]
    return []


# ---------------- Chizish ----------------

def render(data: dict | None) -> Markup:
    """Savol matnidan keyingi ko'rinish (kod, oyna, chizma). Rasm va oddiy jadval — shablonda (test/_question_media.html)."""
    d = data or {}
    out = []
    if d.get("ui"):
        out.append(_toolbar(d["ui"]))
    if d.get("code"):
        out.append(_code(d))
    if d.get("sheet"):
        out.append(_sheet(d["sheet"]))
    if d.get("scratch"):
        out.append(_scratch(d["scratch"]))
    if d.get("logo"):
        out.append(_logo(d["logo"]))
    if d.get("diagram"):
        out.append(Markup('<div class="code"><div class="code-head"><span>{}</span></div><pre data-lang="plain"><code>{}</code></pre></div>')
                   .format(_("Sxema (Mermaid)"), d["diagram"]))
    return Markup("").join(out)


def of(q) -> Markup:
    """Savol dict'i uchun: tayyor "media" bo'lsa — o'sha, aks holda maydonlaridan (namunaviy ekranlar)."""
    return q["media"] if "media" in q else render({k: q[k] for k in KEYS if q.get(k)})


def option(text: str, view: str | None) -> Markup:
    """Variant ko'rinishi. Tugma va chizmada matn ko'rsatilmaydi (javobni aytib qo'ymasin)."""
    if view == "ui" and ui_icons.valid(text):
        return Markup('<span class="ui-btn">{}</span>').format(ui_icons.svg(text))
    if view == "logo":
        return _drawing(text, small=True)
    if view == "code":
        return Markup('<code class="opt-code">{}</code>').format(text)
    return escape(text)


def option_text(text: str, view: str | None) -> str:
    """Variant matn ko'rinishida (ekspert ro'yxati, yechim)."""
    return ui_icons.name(text) if view == "ui" and ui_icons.valid(text) else text


def _code(d: dict) -> Markup:
    lang = norm_lang(d.get("lang"))
    show = d.get("show", "code")
    out = []
    if show != "result":
        out.append(Markup('<div class="code"><div class="code-head"><span>{}</span></div><pre data-lang="{}"><code>{}</code></pre></div>')
                   .format(LANGS[lang], lang, highlight(d["code"], lang)))
    if show != "code" and lang in ("html", "css"):
        body = d["code"] if lang == "html" else f"<style>{_no_close(d['code'])}</style>{d.get('html') or ''}"
        doc = f"<!doctype html><meta charset=utf-8><style>body{{font:16px system-ui;margin:12px;color:#111;background:#fff}}</style>{body}"
        out.append(Markup('<figure class="web-preview"><figcaption>{}</figcaption><iframe sandbox="" srcdoc="{}" title="{}" loading="lazy"></iframe></figure>')
                   .format(_("Brauzerdagi ko‘rinishi"), doc, _("Brauzerdagi ko‘rinishi")))
    return Markup("").join(out)


def _no_close(css: str) -> str:
    """CSS ichidagi «</style» uslubdan chiqib ketmasin (natija baribir skriptsiz oynada)."""
    return re.sub(r"</(?=style)", "<\\/", css, flags=re.I)


def _toolbar(codes: list[str]) -> Markup:
    prog = ui_icons.program(codes[0])
    buttons = Markup("").join(Markup('<span class="ui-btn">{}</span>').format(ui_icons.svg(c)) for c in codes)
    return Markup('<div class="ui-bar" role="img" aria-label="{}"><span class="ui-prog">{}</span>{}</div>').format(
        _("%(p)s dasturining tugmalari", p=prog), prog, buttons)


def _sheet(s: dict) -> Markup:
    rows, active = s["rows"], s.get("active") or ""
    cols = max(len(r) for r in rows)
    letters = "ABCDEFGHIJKL"[:cols]
    head = Markup("").join(Markup('<th scope="col" class="{}">{}</th>').format("on" if active[:1] == c else "", c) for c in letters)
    body = []
    for n, r in enumerate(rows, start=1):
        cells = []
        for k, c in enumerate(letters):
            v = r[k] if k < len(r) else ""
            cls = ["num"] if re.fullmatch(r"-?\d+([.,]\d+)?%?", v) else []
            cls += ["sel"] if f"{c}{n}" == active else []
            cls += ["ask"] if v == "?" else []
            cells.append(Markup('<td class="{}">{}</td>').format(" ".join(cls), v))
        body.append(Markup('<tr><th scope="row" class="{}">{}</th>{}</tr>').format("on" if active[1:] == str(n) else "", n, Markup("").join(cells)))
    bar = Markup('<div class="xl-bar"><span class="xl-cell">{}</span><span class="xl-fx">fx</span><span class="xl-formula">{}</span></div>').format(
        active or "A1", s.get("formula") or "") if active or s.get("formula") else Markup("")
    return Markup('<div class="xl">{}<div class="table-wrap"><table class="xl-grid"><thead><tr><td></td>{}</tr></thead><tbody>{}</tbody></table></div></div>').format(
        bar, head, Markup("").join(body))


# ---------------- Scratch ----------------

def _scratch_tree(src: str) -> list[dict]:
    """Qatorlar → daraxt: [{"cat", "text", "items": [...], "else": [...]}]. Ichkariga kirish — 2 bo'sh joy."""
    root: list[dict] = []
    stack: list[tuple[int, list[dict]]] = [(0, root)]
    for n, raw in enumerate(src.split("\n"), start=1):
        if not raw.strip():
            continue
        line = raw.translate(_APOS)
        level, rest = divmod(len(line) - len(line.lstrip(" ")), 2)
        cat, colon, text = line.strip().partition(":")
        cat, text = cat.strip().lower(), text.strip()
        if rest or not colon or cat not in CATEGORIES or not text:
            raise ValueError(f"{n}-qator: «kategoriya: matn» ko'rinishida, ichkari 2 bo'sh joy bilan ({', '.join(CATEGORIES)})")
        while stack[-1][0] > level:
            stack.pop()
        if stack[-1][0] < level:
            parent = stack[-1][1]
            if level != stack[-1][0] + 1 or not parent:
                raise ValueError(f"{n}-qator: ichkariga kirish noto'g'ri")
            owner = parent[-1]
            stack.append((level, owner["else"] if owner.get("in_else") else owner["items"]))
        if text.lower() == "aks holda":
            if not stack[-1][1] or not stack[-1][1][-1]["items"]:
                raise ValueError(f"{n}-qator: «aks holda» shart blokidan keyin keladi")
            stack[-1][1][-1]["in_else"] = True
            continue
        stack[-1][1].append({"cat": CATEGORIES[cat], "text": text, "items": [], "else": []})
    return root


def _scratch_text(text: str) -> Markup:
    """[10] — son/matn maydoni, (x) — qiymat bloki, <a = b> — shart."""
    out, last = [], 0
    for m in re.finditer(r"\[([^\[\]]*)\]|\(([^()]*)\)|<((?:[^<>]|[<>] )+)>(?=\s|$)", text):
        out.append(escape(text[last:m.start()]))
        kind, value = next((k, v) for k, v in zip(("in", "rep", "bool"), m.groups()) if v is not None)
        out.append(Markup('<span class="sb-{}">{}</span>').format(kind, value))
        last = m.end()
    out.append(escape(text[last:]))
    return Markup("").join(out)


def _scratch_list(items: list[dict]) -> Markup:
    return Markup("").join(Markup('<div class="sb sb-{}{}"><div class="sb-line">{}</div>{}{}</div>').format(
        b["cat"], " sb-c" if b["items"] else "", _scratch_text(b["text"]),
        Markup('<div class="sb-in-list">{}</div>').format(_scratch_list(b["items"])) if b["items"] else "",
        Markup('<div class="sb-line">aks holda</div><div class="sb-in-list">{}</div>').format(_scratch_list(b["else"])) if b["else"] else "")
        for b in items)


def _scratch(src: str) -> Markup:
    try:
        return Markup('<div class="scratch" role="img" aria-label="{}">{}</div>').format(_("Scratch bloklari"), _scratch_list(_scratch_tree(src)))
    except ValueError:
        return Markup('<div class="code"><pre><code>{}</code></pre></div>').format(src)


# ---------------- LOGO ----------------

_LOGO = {"fd": "fd", "forward": "fd", "oldinga": "fd", "bk": "bk", "back": "bk", "backward": "bk", "orqaga": "bk", "rt": "rt", "right": "rt",
         "o‘ngga": "rt", "lt": "lt", "left": "lt", "chapga": "lt", "pu": "pu", "penup": "pu", "pd": "pd", "pendown": "pd", "home": "home",
         "cs": "cs", "clearscreen": "cs", "repeat": "repeat", "takrorla": "repeat"}


def _logo_run(src: str) -> list[tuple[float, float, bool]]:
    """Toshbaqa yo'li: [(x, y, chizildimi)], (0, 0) dan. Noto'g'ri buyruq — ValueError."""
    tokens = re.findall(r"[\[\]]|[^\s\[\]]+", src.translate(_APOS).lower())
    path: list[tuple[float, float, bool]] = [(0.0, 0.0, False)]
    st = {"x": 0.0, "y": 0.0, "a": 90.0, "pen": True, "steps": 0}

    def number(tok):
        if tok is None or not re.fullmatch(r"-?\d{1,4}(\.\d{1,3})?", tok):
            raise ValueError("buyruqdan keyin son kerak")
        return float(tok)

    def block(i, end):
        while i < end:
            st["steps"] += 1
            if st["steps"] > LOGO_STEPS:
                raise ValueError("buyruqlar juda ko'p")
            cmd = _LOGO.get(tokens[i])
            if cmd is None:
                raise ValueError(f"noma'lum buyruq «{tokens[i][:20]}»")
            arg = tokens[i + 1] if i + 1 < end else None
            if cmd == "repeat":
                n = number(arg)
                if not 1 <= n <= 360 or n != int(n) or i + 2 >= end or tokens[i + 2] != "[":
                    raise ValueError("repeat N [ … ] ko'rinishida bo'lsin")
                depth, j = 1, i + 3
                while j < end and depth:
                    depth += {"[": 1, "]": -1}.get(tokens[j], 0)
                    j += 1
                if depth:
                    raise ValueError("qavs yopilmagan")
                for _k in range(int(n)):
                    block(i + 3, j - 1)
                i = j
                continue
            if cmd in ("fd", "bk"):
                d = number(arg) * (1 if cmd == "fd" else -1)
                st["x"] += d * math.cos(math.radians(st["a"]))
                st["y"] += d * math.sin(math.radians(st["a"]))
                path.append((st["x"], st["y"], st["pen"]))
            elif cmd in ("rt", "lt"):
                st["a"] += number(arg) * (-1 if cmd == "rt" else 1)
            elif cmd in ("pu", "pd"):
                st["pen"] = cmd == "pd"
            elif cmd == "home":
                st.update(x=0.0, y=0.0, a=90.0)
                path.append((0.0, 0.0, st["pen"]))
            else:
                st.update(x=0.0, y=0.0, a=90.0, pen=True)
                path[:] = [(0.0, 0.0, False)]
            i += 2 if cmd in ("fd", "bk", "rt", "lt") else 1

    block(0, len(tokens))
    return path


def _logo_errors(src) -> list[str]:
    if not isinstance(src, str) or not src.strip() or len(src) > 1000:
        return ["buyruqlar matni (1000 belgigacha)"]
    try:
        return [] if len(_logo_run(src)) > 1 else ["hech narsa chizilmaydi"]
    except ValueError as e:
        return [str(e)]


def _drawing(src: str, small: bool = False) -> Markup:
    try:
        path = _logo_run(src)
    except ValueError:
        return Markup("<code>{}</code>").format(src)
    xs, ys = [p[0] for p in path], [p[1] for p in path]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    size = max(w, h, 1)
    pad = size * 0.08
    dx, dy = (size - w) / 2 - min(xs) + pad, (size - h) / 2 - min(ys) + pad
    full = size + 2 * pad
    at = lambda x, y: f"{round(x + dx, 1):g} {round(full - (y + dy), 1):g}"                        # noqa: E731
    d = "M" + at(*path[0][:2]) + "".join(("L" if pen else "M") + at(x, y) for x, y, pen in path[1:])
    return Markup('<svg class="logo-draw{}" viewBox="0 0 {} {}" role="img" aria-label="{}"><path d="{}" fill="none" stroke="currentColor" '
                  'stroke-width="{}" stroke-linejoin="round" stroke-linecap="round"/></svg>').format(
        " small" if small else "", f"{full:.1f}", f"{full:.1f}", _("LOGO chizmasi"), d, f"{full / 60:.2f}")


def _logo(logo: dict) -> Markup:
    show, out = logo.get("show", "both"), []
    if show != "drawing":
        out.append(_code({"code": logo["src"], "lang": "logo"}))
    if show != "code":
        out.append(Markup('<figure class="logo-fig">{}</figure>').format(_drawing(logo["src"])))
    return Markup("").join(out)
