"""Har bir ekranning HTML sifati: frontend tekshiruvida qo'lda topilgan xatolar endi avtomatik ushlanadi.

Har bir /ekranlar sahifasi (o'zbek va rus tilida) uchun:
- id'lar takrorlanmaydi; aria-describedby / aria-labelledby / label[for] mavjud id'ga ishora qiladi;
- sahifada bitta <h1> bor; statik <img> da alt bor; har bir maydonning nomi (label yoki aria-label) bor;
- POST formalarda CSRF token bor; inline onclick/onchange yo'q, inline <script> lar nonce'li (CSP);
- ichki havolalar ishlaydi (404/500 emas).
Manba kodi bo'yicha: Alpine ifodalaridagi tarjima JSON qo'shtirnoqda; JS'dagi rmT("kalit") lar tarjima ro'yxatida bor.
Telefon kengligida sig'ish (CSS) brauzersiz tekshirilmaydi — u qo'lda yoki brauzer testida.
"""
import collections
import glob
import re
from html.parser import HTMLParser

import pytest
from flask import url_for

from app.roles import REQUIRED
from app.views.meta import SCREENS

ALL = [(e, t, a) for _, items in SCREENS for e, t, a in items]
IDS = [t for _, t, _ in ALL]


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = collections.Counter()
        self.refs, self.problems, self.links = [], [], set()
        self.h1 = 0
        self.form = None
        self.in_label = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids[a["id"]] += 1
        for k in ("aria-describedby", "aria-labelledby"):
            if a.get(k):
                self.refs += [(k, x) for x in a[k].split()]
        if tag == "label":
            self.in_label += 1
            if a.get("for"):
                self.refs.append(("label[for]", a["for"]))
        if tag == "h1":
            self.h1 += 1
        if tag == "img" and "alt" not in a and ":alt" not in a:
            self.problems.append("img alt'siz: " + a.get("src", "?"))
        if tag == "script" and a.get("type") != "application/json" and "src" not in a and "nonce" not in a:
            self.problems.append("nonce'siz inline <script>")
        inline = [k for k in a if re.fullmatch(r"on[a-z]+", k)]
        if inline:
            self.problems.append(f"inline hodisa ({', '.join(inline)}) — CSP bloklaydi")
        if tag == "a" and (a.get("href") or "").startswith("/") and not a["href"].startswith("//"):
            self.links.add(a["href"].split("#")[0])
        if tag == "form":
            self.form = {"post": (a.get("method") or "").lower() == "post", "csrf": False}
        if tag == "input" and a.get("name") == "csrf_token" and self.form:
            self.form["csrf"] = True
        if tag in ("input", "select", "textarea") and a.get("type") not in ("hidden", "submit", "button", "radio", "checkbox"):
            named = self.in_label or a.get("aria-label") or a.get(":aria-label") or a.get("aria-labelledby") or a.get("title")
            if not named and a.get("id"):
                self.refs.append(("_needs_label", a["id"]))
            elif not named:
                self.problems.append(f"nomsiz maydon: <{tag} name={a.get('name')}>")

    def handle_endtag(self, tag):
        if tag == "label":
            self.in_label -= 1
        if tag == "form" and self.form is not None:
            if self.form["post"] and not self.form["csrf"]:
                self.problems.append("POST forma CSRF tokensiz")
            self.form = None

    def check(self):
        out = list(self.problems)
        out += [f"takroriy id: {i}" for i, n in self.ids.items() if n > 1]
        labelled = {x for k, x in self.refs if k == "label[for]"}
        for k, x in self.refs:
            if k == "_needs_label":
                if x not in labelled:
                    out.append(f"label'siz maydon: #{x}")
            elif x not in self.ids:
                out.append(f"{k} → yo'q id: {x}")
        if self.h1 != 1:
            out.append(f"<h1> soni {self.h1} (1 ta bo'lishi kerak)")
        return out


def _get(app, as_role, endpoint, args, lang):
    with app.test_request_context():
        url = url_for(endpoint, **args)
    c = as_role(REQUIRED.get(endpoint.split(".")[0], "user"))
    return c, c.get(url + ("&" if "?" in url else "?") + "til=" + lang, follow_redirects=True)


@pytest.mark.parametrize("lang", ["uz", "ru"])
@pytest.mark.parametrize("endpoint,title,args", ALL, ids=IDS)
def test_page_quality(app, as_role, endpoint, title, args, lang):
    _, r = _get(app, as_role, endpoint, args, lang)
    p = Page()
    p.feed(r.get_data(as_text=True))
    assert p.check() == [], f"{title} [{lang}]"
    assert "Content-Security-Policy" in r.headers


@pytest.mark.parametrize("endpoint,title,args", ALL, ids=IDS)
def test_internal_links_work(app, as_role, endpoint, title, args):
    c, r = _get(app, as_role, endpoint, args, "uz")
    p = Page()
    p.feed(r.get_data(as_text=True))
    broken = []
    for link in sorted(p.links):
        if link.startswith(("/chiqish", "/_rol/")):
            continue
        code = c.get(link).status_code
        if code >= 400 and not (code in (404, 410) and link.startswith(("/s/", "/taklif/"))):
            broken.append(f"{code} {link}")
    assert broken == [], title


def test_alpine_translations_are_json_quoted():
    """'{{ _("…") }}' JS satri ichida — tarjimada apostrof bo'lsa Alpine ifodasi buziladi. |tojson|forceescape kerak."""
    bad = [f for f in glob.glob("app/templates/**/*.html", recursive=True)
           if re.search(r"'\{\{ _\(", open(f, encoding="utf8").read())]
    assert bad == []


def test_js_translation_keys_exist():
    """JS'dagi har bir rmT("kalit") base.html dagi tarjima ro'yxatida va JS'dagi o'zbekcha zaxirada bor."""
    js = "".join(open(f, encoding="utf8").read() for f in glob.glob("app/static/js/*.js"))
    js = re.sub(r"/\*.*?\*/|^\s*//.*$", "", js, flags=re.S | re.M)   # izohlardagi misollar hisobga olinmaydi
    base = open("app/templates/base.html", encoding="utf8").read()
    core = open("app/static/js/core.js", encoding="utf8").read()
    uz = core[core.index("var UZ = {"):core.index("};", core.index("var UZ = {"))]
    for key in set(re.findall(r'rmT\("([a-zA-Z]+)"', js)):
        assert f'"{key}":' in base, f"base.html rm-i18n da yo'q: {key}"
        assert re.search(rf"\b{key}:", uz), f"core.js UZ da yo'q: {key}"
