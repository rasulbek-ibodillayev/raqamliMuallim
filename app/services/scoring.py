"""Baholash qoidalari (B1, 2026-11-23 da tasdiqlangan).

- Bitta javobli: to'g'ri — 100, aks holda 0.
- Ko'p javobli: (to'g'ri belgilangan − noto'g'ri belgilangan) ÷ jami to'g'ri; manfiy bo'lsa 0.
- Moslashtirish: har bir to'g'ri juftlik uchun teng ulush.
- Ochiq javob: answer.value yoki answer.accept dan biriga teng bo'lsa 100. Katta-kichik harf, ortiqcha bo'sh joy
  va tutuq belgisining yozilishi (o‘ / o' / oʻ) farqlanmaydi.
- Urinish foizi — savollar ballining o'rtachasi, butun songacha yaxlitlanadi; qaror shu yaxlitlangan foiz bo'yicha:
  < 70 — fail (qayta o'zlashtiriladi), 70–89 — warn (tavsiya bilan), ≥ 90 — pass.
"""
import re

PASS_MIN, SOLID_MIN = 70, 90


def _half_up(x: float) -> int:
    """Python'ning round() i yarimni juft songa yaxlitlaydi (66.5 → 66); bizga odatdagi yaxlitlash kerak."""
    return int(x + 0.5)


def _indexes(v) -> set[int]:
    return {x for x in v if isinstance(x, int) and not isinstance(x, bool)} if isinstance(v, list) else set()


def norm_text(s) -> str:
    s = re.sub(r"\s+", " ", str(s)).strip().casefold()
    return re.sub("[‘’ʻʼ`']", "'", s)


def grade(qtype: str, answer: dict, value) -> int:
    """Bitta javob bali, 0..100. value — pleyer yuborgan javob (indeks, indekslar ro'yxati yoki matn)."""
    if value is None:
        return 0
    if qtype == "single":
        return 100 if not isinstance(value, bool) and value in answer.get("keys", []) else 0
    if qtype == "multiple":
        keys, mine = set(answer.get("keys", [])), _indexes(value)
        if not keys:
            return 0
        return _half_up(100 * max(0, len(mine & keys) - len(mine - keys)) / len(keys))
    if qtype == "matching":
        pairs = answer.get("pairs", [])
        if not pairs or not isinstance(value, list):
            return 0
        hits = sum(1 for mine, right in zip(value, pairs) if mine is not None and mine == right)
        return _half_up(100 * hits / len(pairs))
    if qtype == "open":
        if not isinstance(value, str) or not value.strip():
            return 0
        return 100 if norm_text(value) in {norm_text(x) for x in [answer.get("value", ""), *answer.get("accept", [])]} else 0
    return 0


def percent(scores: list[int]) -> int:
    """Savollar bali (0..100) → urinish foizi."""
    return _half_up(sum(scores) / len(scores)) if scores else 0


def decision(pct: int) -> str:
    return "fail" if pct < PASS_MIN else ("warn" if pct < SOLID_MIN else "pass")
