"""Google Fonts shriftlarini loyiha ichiga ko'chiradi (oflayn PWA, sekin internet, maxfiylik).

    .venv/Scripts/python scripts/vendor_fonts.py

Natija: app/static/fonts/*.woff2 va app/static/css/fonts-<nom>.css.
Faqat kerakli subsetlar olinadi: latin, latin-ext, cyrillic, cyrillic-ext (o'zbek lotin va rus tili).
Shriftlar SIL Open Font License ostida.
"""
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "app" / "static"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
SUBSETS = {"latin", "latin-ext", "cyrillic", "cyrillic-ext"}
FONTS = {
    "cert": "https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;0,700;1,500&display=swap",
    "exam": "https://fonts.googleapis.com/css2?family=Montserrat+Alternates:wght@400;500;600;700&display=swap",
}


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def main():
    (ROOT / "fonts").mkdir(exist_ok=True)
    for name, url in FONTS.items():
        css = get(url).decode()
        out = [f"/* {name}: Google Fonts'dan ko'chirilgan (scripts/vendor_fonts.py). Litsenziya: SIL OFL 1.1 */"]
        for subset, block in re.findall(r"/\* ([\w-]+) \*/\s*(@font-face \{.*?\})", css, re.S):
            if subset not in SUBSETS:
                continue
            fam = re.search(r"font-family: '([^']+)'", block).group(1)
            style = re.search(r"font-style: (\w+)", block).group(1)
            weight = re.search(r"font-weight: (\d+)", block).group(1)
            src = re.search(r"url\((https://[^)]+\.woff2)\)", block).group(1)
            fname = f"{fam.lower().replace(' ', '-')}-{weight}{'i' if style == 'italic' else ''}-{subset}.woff2"
            (ROOT / "fonts" / fname).write_bytes(get(src))
            out.append(f"/* {subset} */\n" + block.replace(src, f"../fonts/{fname}"))
        (ROOT / "css" / f"fonts-{name}.css").write_text("\n".join(out) + "\n", encoding="utf-8")
        print(name, len(out) - 1, "ta @font-face")


if __name__ == "__main__":
    main()
