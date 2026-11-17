"""Shablonlardagi statik matnlarni `{{ _("...") }}` ga o'raydi (bir martalik refaktor vositasi).

    python scripts/wrap_i18n.py [--dry]

O'raladi:
  - teglar orasidagi oddiy matn (ichida Jinja ifodasi bo'lmasa);
  - placeholder, aria-label, title, alt atributlarining statik qiymatlari.
O'ralmaydi:
  - <script>, <style>, <pre>, <code>, <svg>, <textarea> ichidagilar, Jinja izohlari;
  - Alpine bog'lamlari (:attr, x-text, @click ...), Jinja ifodali matnlar (aralash satrlar);
  - harfsiz satrlar (raqam, belgi), allaqachon o'ralganlar.
Foiz belgisi `%%` qilinadi (Jinja newstyle gettext). Natija HTML'i o'zgarmasligi
scripts/snapshot_screens.py bilan tekshiriladi.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "app" / "templates"

# Token: Jinja izohi | Jinja bloki | Jinja ifodasi | HTML izohi | HTML tegi (qo'shtirnoqlarni hisobga olib) | matn
TOKEN_RE = re.compile(
    r"(\{#.*?#\})|(\{%.*?%\})|(\{\{.*?\}\})|(<!--.*?-->)|(<(?:[^<>\"']|\"[^\"]*\"|'[^']*')*>)", re.S)
SKIP_TAGS = {"script", "style", "pre", "code", "svg", "textarea"}
LETTER_RE = re.compile(r"[A-Za-zА-Яа-яЁёЎўҚқҒғҲҳ]")
ATTR_RE = re.compile(r'(?<![:\w@.-])(placeholder|aria-label|title|alt)="([^"]*)"')


def quote(text: str) -> str | None:
    if "\\" in text:
        return None
    t = text.replace("%", "%%")
    if '"' not in t:
        return f'"{t}"'
    if "'" not in t:
        return f"'{t}'"
    return None


def wrap_text(chunk: str) -> str:
    stripped = chunk.strip()
    if not stripped or len(LETTER_RE.findall(stripped)) < 2:
        return chunk
    q = quote(stripped)
    if q is None:
        return chunk
    lead = chunk[: len(chunk) - len(chunk.lstrip())]
    tail = chunk[len(chunk.rstrip()):]
    return f"{lead}{{{{ _({q}) }}}}{tail}"


def wrap_attrs(tag: str) -> str:
    def repl(m):
        name, val = m.group(1), m.group(2)
        if "{{" in val or "{%" in val or len(LETTER_RE.findall(val)) < 2:
            return m.group(0)
        q = quote(val)
        if q is None or q.startswith('"'):
            # atribut qo'shtirnoqda — ichida bittalik qo'shtirnoq ishlatamiz
            if "'" in val:
                return m.group(0)
            q = "'" + val.replace("%", "%%") + "'"
        return f'{name}="{{{{ _({q}) }}}}"'
    return ATTR_RE.sub(repl, tag)


def process(src: str):
    out, pos, stack, count = [], 0, [], 0
    for m in TOKEN_RE.finditer(src):
        text = src[pos:m.start()]
        if text:
            new = text if stack else wrap_text(text)
            count += new != text
            out.append(new)
        tok = m.group(0)
        if m.group(5):  # HTML tegi
            tm = re.match(r"<\s*(/)?\s*([a-zA-Z][\w:-]*)", tok)
            if tm:
                closing, name = tm.group(1), tm.group(2).lower()
                if name in SKIP_TAGS:
                    if closing:
                        if stack and stack[-1] == name:
                            stack.pop()
                    elif not tok.endswith("/>"):
                        stack.append(name)
                if not stack and not closing:
                    new = wrap_attrs(tok)
                    count += new != tok
                    tok = new
        out.append(tok)
        pos = m.end()
    rest = src[pos:]
    new = rest if stack else wrap_text(rest)
    count += new != rest
    out.append(new)
    return "".join(out), count


def main(dry=False):
    total = 0
    for p in sorted(ROOT.rglob("*.html")):
        src = p.read_text(encoding="utf-8")
        new, n = process(src)
        total += n
        if n and not dry:
            p.write_text(new, encoding="utf-8")
        if n:
            print(f"{n:4d}  {p.relative_to(ROOT)}")
    print("Jami o'ralgan:", total)


if __name__ == "__main__":
    main(dry="--dry" in sys.argv)
