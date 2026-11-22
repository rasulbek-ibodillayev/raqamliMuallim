"""Eski nom saqlanib qolgan: endi barcha tillar scripts/translate.py orqali to'ldiriladi.

    .venv/Scripts/python scripts/apply_translations.py   ==   .venv/Scripts/python scripts/translate.py
"""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).with_name("translate.py")), run_name="__main__")
