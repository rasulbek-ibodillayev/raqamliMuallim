"""Python fayllaridagi foydalanuvchiga ko'rinadigan xabarlarni gettext `_()` ga o'raydi (bir martalik).

Faqat funksiya ichidagi oddiy satrlar (docstring emas, f-string emas), ichida bo'sh joy va harf bo'lsa.
Modul darajasidagi doimiylar (REGIONS kabi ma'lumotlar) o'zgarmaydi: ular so'rovdan tashqarida yuklanadi.
"""
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "app"
FILES = ["forms.py", "views/auth.py", "views/user.py", "views/admin.py", "views/api.py"]
LETTERS = re.compile(r"[A-Za-z‘’]{2}")
IMPORT = "from flask_babel import gettext as _\n"


def offsets(src):
    starts, acc = [], 0
    for line in src.splitlines(keepends=True):
        starts.append(acc)
        acc += len(line.encode("utf-8"))
    return starts


def main(dry=False):
    for rel in FILES:
        p = ROOT / rel
        src = p.read_text(encoding="utf-8")
        tree = ast.parse(src)
        raw = src.encode("utf-8")
        starts = offsets(src)
        docstrings = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.Module)) and node.body and isinstance(node.body[0], ast.Expr) \
                    and isinstance(node.body[0].value, ast.Constant):
                docstrings.add(id(node.body[0].value))
        fstring_parts = {id(v) for n in ast.walk(tree) if isinstance(n, ast.JoinedStr) for v in n.values}
        spans = []
        for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
            for node in ast.walk(fn):
                if (isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings
                        and id(node) not in fstring_parts and " " in node.value and LETTERS.search(node.value)):
                    s = starts[node.lineno - 1] + node.col_offset
                    e = starts[node.end_lineno - 1] + node.end_col_offset
                    seg = raw[s:e].decode("utf-8")
                    if seg[0] in "\"'":   # prefiksli (f/r/b) satrlarni o'tkazib yuboramiz
                        spans.append((s, e))
        if not spans:
            continue
        out = raw
        for s, e in sorted(set(spans), reverse=True):
            out = out[:s] + b"_(" + out[s:e] + b")" + out[e:]
        text = out.decode("utf-8")
        if IMPORT not in text:
            # birinchi "from flask ..." importidan keyin qo'shamiz
            m = re.search(r"^from flask import [^\n]*(?:\n[ \t]+[^\n]*)*\n", text, re.M)
            text = text[:m.end()] + IMPORT + text[m.end():] if m else IMPORT + text
        print(f"{len(spans):3d}  {rel}")
        if not dry:
            p.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main(dry="--dry" in sys.argv)
