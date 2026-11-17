"""Barcha ekranlar HTML'ini faylga yozadi (refaktordan oldin va keyin solishtirish uchun).

    .venv/Scripts/python scripts/snapshot_screens.py <papka>
    .venv/Scripts/python scripts/snapshot_screens.py <papka> --diff <oldingi_papka>

CSRF tokeni har so'rovda boshqacha bo'lgani uchun u bir xil qiymatga almashtiriladi.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402
from app.roles import REQUIRED  # noqa: E402
from app.views.meta import SCREENS  # noqa: E402

CSRF_RE = re.compile(r'(name="csrf_token" value="|name="csrf-token" content=")[^"]+"')


def snapshot(out: Path):
    app = create_app()
    out.mkdir(parents=True, exist_ok=True)
    from flask import url_for
    with app.test_request_context():
        items = [(url_for(e, **a), REQUIRED.get(e.split(".")[0])) for _, g in SCREENS for e, _, a in g]
    for i, (url, role) in enumerate(items):
        c = app.test_client()
        if role:
            c.get(f"/_rol/{role}")
        html = c.get(url).get_data(as_text=True)
        html = CSRF_RE.sub(r'\1X"', html)
        (out / f"{i:03d}.html").write_text(f"<!-- {url} -->\n{html}", encoding="utf-8")
    return len(items)


def diff(a: Path, b: Path):
    bad = []
    for f in sorted(a.glob("*.html")):
        g = b / f.name
        if not g.exists() or f.read_text(encoding="utf-8") != g.read_text(encoding="utf-8"):
            bad.append(f.read_text(encoding="utf-8").splitlines()[0])
    return bad


if __name__ == "__main__":
    out = Path(sys.argv[1])
    n = snapshot(out)
    print(n, "ekran saqlandi:", out)
    if "--diff" in sys.argv:
        bad = diff(Path(sys.argv[sys.argv.index("--diff") + 1]), out)
        print("Farq qilgan ekranlar:", len(bad))
        for line in bad[:20]:
            print(" ", line)
