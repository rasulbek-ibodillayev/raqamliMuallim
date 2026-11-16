"""PWA uchun PNG ikonkalarni app/static/icon.svg dizayni asosida yaratadi.

    .venv/Scripts/pip install pillow   # faqat shu skript uchun, ilovaga kerak emas
    .venv/Scripts/python scripts/make_icons.py

Natija: app/static/icons/ — icon-192.png, icon-512.png (yumaloq burchak, "any"),
maskable-512.png (to'liq fon, belgi xavfsiz zonada), apple-touch-icon.png (180, shaffofliksiz), favicon-32.png.
"""
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "app" / "static" / "icons"
STOPS = [(0.0, (0x63, 0x66, 0xF1)), (0.55, (0x25, 0x63, 0xEB)), (1.0, (0x06, 0xB6, 0xD4))]
# icon.svg dagi yulduz (64x64 koordinatalarda)
STAR = [(29, 14), (34, 27.5), (47.5, 32), (34, 37), (29, 50.5), (24, 37), (10.5, 32), (24, 27.5)]
SS = 4  # silliq chiziqlar uchun katta o'lchamda chizib, keyin kichraytiramiz


def lerp_color(t):
    for (t0, c0), (t1, c1) in zip(STOPS, STOPS[1:]):
        if t <= t1:
            k = (t - t0) / (t1 - t0)
            return tuple(round(a + (b - a) * k) for a, b in zip(c0, c1))
    return STOPS[-1][1]


def gradient(n):
    # Diagonal (yuqori-chapdan pastki-o'ngga) gradient: har diagonal chiziq bir xil rangda
    lut = [lerp_color(i / 510) for i in range(511)]
    img = Image.new("RGB", (n, n))
    px = img.load()
    for y in range(n):
        for x in range(n):
            px[x, y] = lut[round((x + y) / (2 * (n - 1)) * 510)]
    return img


def render(size, *, rounded, star_scale=1.0):
    n = size * SS
    img = gradient(n).convert("RGBA")
    if rounded:
        mask = Image.new("L", (n, n), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, n - 1, n - 1], radius=n * 18 / 64, fill=255)
        img.putalpha(mask)
    # Yulduzni kanvas markaziga qo'yamiz va kerak bo'lsa kichraytiramiz (maskable uchun xavfsiz zona)
    cx, cy = 29, 32.25  # SVG'dagi yulduz markazi
    pts = [((32 + (x - cx) * star_scale) * n / 64, (32 + (y - cy) * star_scale) * n / 64) for x, y in STAR]
    ImageDraw.Draw(img).polygon(pts, fill="white")
    return img.resize((size, size), Image.LANCZOS)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    render(192, rounded=True).save(OUT / "icon-192.png", optimize=True)
    render(512, rounded=True).save(OUT / "icon-512.png", optimize=True)
    render(32, rounded=True).save(OUT / "favicon-32.png", optimize=True)
    # Maskable: OS o'zi kesadi (doira/kvadrat), belgi markaziy 80% ichida qolishi kerak
    render(512, rounded=False, star_scale=0.8).save(OUT / "maskable-512.png", optimize=True)
    # iOS shaffoflikni qora qiladi va burchaklarni o'zi yumaloqlaydi
    render(180, rounded=False).convert("RGB").save(OUT / "apple-touch-icon.png", optimize=True)
    print("Tayyor:", ", ".join(sorted(p.name for p in OUT.glob("*.png"))))


if __name__ == "__main__":
    main()
