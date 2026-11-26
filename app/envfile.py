"""`.env` faylini o'qish (qo'shimcha kutubxonasiz). run.py va worker.py ishlatadi."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env(path: Path = ROOT / ".env") -> None:
    """KALIT=qiymat qatorlari; muhitda bor qiymat ustun turadi."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and key.strip() and not key.startswith("#"):
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))
