"""UI makrolarining matnli argumentlarini `_()` ga o'raydi (wrap_i18n.py ning davomi, bir martalik).

Faqat foydalanuvchiga ko'rinadigan argumentlar: page_head(sarlavha, izoh), badge(matn), status_dot(matn),
ring(..., label), composer(placeholder). Rang/ikonka nomlari (kichik harfli, bo'sh joysiz) o'zgarmaydi.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "app" / "templates"
CALL_RE = re.compile(r"\b(page_head|badge|status_dot|ring|composer)\(")
STR_RE = re.compile(r'(?<![\w_(])"([^"\\]*)"')
UI_TEXT = re.compile(r"[A-ZА-Я‘’ʻ…]|\s")


def args_span(src, start):
    """Ochilgan qavsdan yopilgunigacha (ichki qavslarni hisobga olib)."""
    depth, i, q = 0, start, None
    while i < len(src):
        ch = src[i]
        if q:
            if ch == q:
                q = None
        elif ch in "\"'":
            q = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def process(src):
    out, pos, n = [], 0, 0
    for m in CALL_RE.finditer(src):
        if m.start() < pos:
            continue
        # makro ta'rifi ({% macro badge(...) %}) emas, chaqiruv bo'lishi kerak
        if src[max(0, m.start() - 6):m.start()] == "macro ":
            continue
        open_i = m.end() - 1
        close_i = args_span(src, open_i)
        if close_i < 0:
            continue
        inner = src[open_i + 1:close_i]

        def repl(sm):
            nonlocal n
            text = sm.group(1)
            if not UI_TEXT.search(text) or text.startswith(("var(", "#")):
                return sm.group(0)
            n += 1
            return '_("' + text.replace("%", "%%") + '")'
        new_inner = STR_RE.sub(repl, inner)
        out.append(src[pos:open_i + 1] + new_inner)
        pos = close_i
    out.append(src[pos:])
    return "".join(out), n


def main(dry=False):
    total = 0
    for p in sorted(ROOT.rglob("*.html")):
        if p.name == "_ui.html":
            continue
        src = p.read_text(encoding="utf-8")
        new, n = process(src)
        total += n
        if n and not dry:
            p.write_text(new, encoding="utf-8")
    print("O'ralgan argumentlar:", total)


if __name__ == "__main__":
    main(dry="--dry" in sys.argv)
