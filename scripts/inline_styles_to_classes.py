"""Shablonlardagi statik inline `style="..."` larni utility klasslarga aylantiradi (bir martalik refaktor vositasi).

    python scripts/inline_styles_to_classes.py          # o'zgartiradi
    python scripts/inline_styles_to_classes.py --dry    # faqat hisobot

- Har bir deklaratsiya `u-` prefiksli atomik klassga aylanadi (masalan, margin:0 → u-m-0, padding:12px 14px → u-p-12-14).
- Klasslar `!important` bilan yoziladi: inline uslub kabi har qanday komponent qoidasidan ustun turadi,
  shuning uchun ko'rinish o'zgarmaydi.
- Jinja ifodali (`{{ ... }}`) uslublar — ma'lumotdan keladigan qiymatlar (progress foizi, rang) — o'zgartirilmaydi:
  ular uchun CSS custom property (`--v`, `--d`) qoldirilgani to'g'ri yondashuv.
- Alpine `:style` bog'lamlariga tegilmaydi.
Natija app/static/css/utilities.css ga yoziladi (avtomatik qism).
"""
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "app"
OUT = ROOT / "static" / "css" / "utilities.css"

ABBR = {
    "margin": "m", "margin-top": "mt", "margin-bottom": "mb", "margin-left": "ml", "margin-right": "mr",
    "padding": "p", "padding-top": "pt", "padding-bottom": "pb", "padding-left": "pl", "padding-right": "pr",
    "width": "w", "height": "h", "min-width": "minw", "min-height": "minh", "max-width": "maxw", "max-height": "maxh",
    "font-size": "fs", "font-weight": "fw", "gap": "gap", "border-radius": "r", "text-align": "ta", "cursor": "cur",
    "display": "d", "list-style": "ls", "opacity": "op", "white-space": "ws", "position": "pos", "top": "top",
    "bottom": "bottom", "color": "c", "background": "bg", "border": "b", "border-top": "bt", "accent-color": "accent",
    "justify-content": "jc", "align-items": "ai", "grid-template-columns": "cols", "flex-direction": "fd",
    "align-self": "as", "font-family": "ff", "border-width": "bw", "line-height": "lh", "overflow": "of",
}
VAR_NAMES = {"var(--border)": "border", "var(--text-2)": "text2", "var(--primary)": "primary", "var(--bg)": "bg",
             "var(--mono)": "mono", "var(--surface-2)": "surface2", "var(--primary-soft)": "primary-soft"}

STYLE_RE = re.compile(r'(?<![:\w-])style="([^"]*)"')


def token(value: str) -> str:
    v = value.strip()
    for k, name in VAR_NAMES.items():
        v = v.replace(k, name)
    v = v.replace("1px solid border", "1").replace("%", "p").replace("px", "").replace(".", "_")
    v = re.sub(r"\s+", "-", v)
    if re.fullmatch(r"[a-z0-9_-]+", v):
        return v
    return hashlib.md5(value.encode()).hexdigest()[:5]   # calc(), minmax() kabi murakkab qiymatlar


def class_for(prop: str, value: str) -> str:
    return f"u-{ABBR.get(prop, prop)}-{token(value)}"


def parse(style: str):
    out = []
    for decl in style.split(";"):
        if not decl.strip():
            continue
        prop, _, value = decl.partition(":")
        out.append((prop.strip().lower(), value.strip()))
    return out


def main(dry=False):
    rules, changed, skipped = {}, 0, 0
    for path in sorted((ROOT / "templates").rglob("*.html")):
        src = path.read_text(encoding="utf-8")
        new_src, pos, parts = src, 0, []
        for m in STYLE_RE.finditer(src):
            style = m.group(1)
            if "{{" in style or "{%" in style:
                skipped += 1
                continue
            classes = []
            for prop, value in parse(style):
                cls = class_for(prop, value)
                rules[cls] = f"{prop}: {value} !important;"
                classes.append(cls)
            # Shu tegning class atributini topamiz (style'dan oldin yoki keyin)
            tag_start = src.rfind("<", 0, m.start())
            tag_end = src.find(">", m.end())
            tag = src[tag_start:tag_end + 1]
            rel_s, rel_e = m.start() - tag_start, m.end() - tag_start
            new_tag = tag[:rel_s].rstrip() + tag[rel_e:]
            cm = re.search(r'(?<![:\w-])class="([^"]*)"', new_tag)
            if cm:
                new_tag = new_tag[:cm.end(1)] + " " + " ".join(classes) + new_tag[cm.end(1):]
            else:
                name_end = re.match(r"<[\w:-]+", new_tag).end()
                new_tag = new_tag[:name_end] + f' class="{" ".join(classes)}"' + new_tag[name_end:]
            parts.append((tag_start, tag_end + 1, new_tag))
            changed += 1
        if parts:
            # Bir tegda bir nechta style bo'lmaydi; oxiridan boshlab almashtiramiz
            for s, e, t in sorted(parts, reverse=True):
                new_src = new_src[:s] + t + new_src[e:]
            if not dry:
                path.write_text(new_src, encoding="utf-8")
    css = ["/* Avtomatik: scripts/inline_styles_to_classes.py. Shablonlardagi bir martalik inline uslublar o'rniga.",
           "   !important — inline uslub kabi komponent qoidalaridan ustun turishi uchun. */"]
    css += [f".{c} {{ {d} }}" for c, d in sorted(rules.items())]
    if not dry:
        OUT.write_text("\n".join(css) + "\n", encoding="utf-8")
    print(f"o'zgartirildi: {changed}, Jinja ifodali (qoldirildi): {skipped}, klasslar: {len(rules)}")


if __name__ == "__main__":
    main(dry="--dry" in sys.argv)
