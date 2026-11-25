import os
from pathlib import Path

from app import create_app


def load_env(path: Path) -> None:
    """.env dagi KALIT=qiymat qatorlari (muhitda bor qiymat ustun turadi). Qo'shimcha kutubxona kerak emas."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and key.strip() and not key.startswith("#"):
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


load_env(Path(__file__).with_name(".env"))
if __name__ == "__main__":
    os.environ.setdefault("FLASK_DEBUG", "1")      # ishlab chiqish: SECRET_KEY shart emas, cookie http'da ham ishlaydi
app = create_app()

if __name__ == "__main__":
    # PORT muhit o'zgaruvchisi berilsa, o'sha portda ishlaydi (standart: 5000)
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
