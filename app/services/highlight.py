"""Kodni ranglash (serverda): Python, JavaScript, HTML, CSS, SQL, LOGO va boshqalar. Natija — xavfsiz HTML (hammasi ekranlanadi).

Serverda qilingani uchun pleyer, natija, AI tutor suhbati va oflayn sahifalarda bir xil; brauzerga kutubxona yuklanmaydi.
"""
import re

from markupsafe import Markup, escape

# Til kodi → ko'rsatiladigan nom (data.lang qiymatlari)
LANGS = {"python": "Python", "javascript": "JavaScript", "html": "HTML", "css": "CSS", "sql": "SQL", "logo": "LOGO", "cpp": "C++",
         "java": "Java", "pascal": "Pascal", "csharp": "C#", "php": "PHP", "bash": "Terminal", "plain": "Matn"}
ALIASES = {"js": "javascript", "c++": "cpp", "c#": "csharp", "py": "python", "terminal": "bash", "matn": "plain", "text": "plain"}

_WORDS = {
    "python": "False None True and as assert async await break class continue def del elif else except finally for from global if import "
              "in is lambda nonlocal not or pass raise return try while with yield",
    "javascript": "await break case catch class const continue default delete do else false finally for function if in instanceof let new "
                  "null of return switch this throw true try typeof undefined var while",
    "sql": "select from where and or not insert into values update set delete create table primary key foreign references join left right "
           "inner on group by order having count sum avg min max as distinct limit null like between in",
    "cpp": "auto bool break case char class const continue default delete do double else false float for if int long namespace new return "
           "short sizeof string struct switch true using void while include cout cin endl",
    "java": "boolean break case char class const continue default do double else extends false final float for if import int long new null "
            "package private public return static String switch this true void while",
    "pascal": "and array begin case const div do downto else end for function if integer mod not of or procedure program real repeat string "
              "then to until uses var while write writeln read readln boolean",
    "logo": "fd forward bk back rt right lt left pu penup pd pendown repeat to end home cs clearscreen setpc setwidth ifelse if stop make",
    "bash": "cd ls mkdir rm cp mv cat echo ping ipconfig dir copy del"}
_WORDS["csharp"] = _WORDS["java"]
_WORDS["php"] = _WORDS["javascript"] + " echo foreach as"
_NOCASE = {"sql", "pascal", "logo"}
_COMMENT = {"python": r"#[^\n]*", "javascript": r"//[^\n]*|/\*.*?\*/", "sql": r"--[^\n]*", "cpp": r"//[^\n]*|/\*.*?\*/",
            "java": r"//[^\n]*|/\*.*?\*/", "csharp": r"//[^\n]*|/\*.*?\*/", "php": r"//[^\n]*|/\*.*?\*/|#[^\n]*",
            "pascal": r"\{.*?\}|//[^\n]*", "logo": r";[^\n]*", "bash": r"#[^\n]*"}
_STRING = r"\"(?:\\.|[^\"\\\n])*\"|'(?:\\.|[^'\\\n])*'|`(?:\\.|[^`\\])*`"
_HTML = re.compile(r"(?P<c><!--.*?-->)|(?P<k></?[A-Za-z][\w-]*|/?>)|(?P<s>\"[^\"]*\"|'[^']*')|(?P<f>[\w-]+(?==))", re.S)
_CSS = re.compile(r"(?P<c>/\*.*?\*/)|(?P<s>\"[^\"]*\"|'[^']*')|(?P<f>[\w-]+(?=\s*:))|(?P<n>#[0-9a-fA-F]{3,8}\b|-?\d+(?:\.\d+)?(?:px|em|rem|%|vh|vw|s|deg)?)"
                  r"|(?P<k>[.#]?[A-Za-z][\w-]*(?=[^;{}]*\{))", re.S)


def norm_lang(lang: str | None) -> str:
    v = (lang or "python").strip().lower()
    v = ALIASES.get(v, v)
    return v if v in LANGS else next((k for k, n in LANGS.items() if n.lower() == v), "plain")


def _pattern(lang: str):
    words = "|".join(_WORDS[lang].split())
    return re.compile(rf"(?P<c>{_COMMENT[lang]})|(?P<s>{_STRING})|(?P<n>\b\d+(?:\.\d+)?\b)|(?P<k>\b(?:{words})\b)|(?P<f>\b[A-Za-z_]\w*(?=\s*\())",
                      re.S | (re.I if lang in _NOCASE else 0))


_PATTERNS = {**{k: _pattern(k) for k in _WORDS}, "html": _HTML, "css": _CSS}


def highlight(src: str, lang: str | None) -> Markup:
    """Ranglangan kod. Noma'lum til — oddiy matn."""
    pattern = _PATTERNS.get(norm_lang(lang))
    if pattern is None:
        return escape(src)
    out, last = [], 0
    for m in pattern.finditer(src):
        out.append(escape(src[last:m.start()]))
        out.append(Markup('<span class="tok-{}">{}</span>').format(m.lastgroup, m.group()))
        last = m.end()
    out.append(escape(src[last:]))
    return Markup("").join(out)
