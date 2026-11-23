"""Baholash qoidalari (B1): qisman ball, ochiq javob, foiz va qaror."""
import pytest

from app.services import scoring as s


@pytest.mark.parametrize("value,score", [(1, 100), (0, 0), (None, 0), (True, 0), ("1", 0), ([1], 0)])
def test_single(value, score):
    assert s.grade("single", {"keys": [1]}, value) == score


@pytest.mark.parametrize("value,score", [
    ([0, 2, 4], 100),
    ([0, 2], 67),            # 2/3
    ([0], 33),
    ([0, 2, 1], 33),         # 2 to'g'ri − 1 noto'g'ri = 1/3
    ([0, 1], 0),             # 1 − 1
    ([1, 3], 0),             # manfiy bo'lmaydi
    ([0, 1, 2, 3, 4], 33),   # hammasini belgilash: 3 − 2 = 1/3
    ([0, 0, 0], 33),         # takror hisoblanmaydi
    ([], 0), (None, 0), (0, 0),
])
def test_multiple_partial(value, score):
    assert s.grade("multiple", {"keys": [0, 2, 4]}, value) == score


@pytest.mark.parametrize("value,score", [
    ([1, 0, 2], 100), ([1, 0, None], 67), ([1, 2, 0], 33), ([0, 1, 2], 33), ([None, None, None], 0), ([1], 33), ("x", 0),
])
def test_matching_partial(value, score):
    assert s.grade("matching", {"pairs": [1, 0, 2]}, value) == score


@pytest.mark.parametrize("value,score", [
    ("45", 100), (" 45 ", 100), ("45₁₀", 100), ("QIRQ  besh", 100), ("46", 0), ("", 0), ("  ", 0), (45, 0),
])
def test_open_accepts_list(value, score):
    assert s.grade("open", {"value": "45", "accept": ["45₁₀", "qirq besh"]}, value) == score


def test_open_apostrophes_are_equal():
    for v in ("o‘zgaruvchi", "o'zgaruvchi", "Oʻzgaruvchi", "o’zgaruvchi"):
        assert s.grade("open", {"value": "o‘zgaruvchi"}, v) == 100


def test_percent_and_decision():
    assert s.percent([100, 100, 33]) == 78            # 3 savollik dars testida 70–89% chiqadi
    assert s.percent([100, 100, 0]) == 67 and s.percent([]) == 0
    assert s.percent([100, 33]) == 67                 # 66.5 → 67
    assert [s.decision(p) for p in (0, 69, 70, 89, 90, 100)] == ["fail", "fail", "warn", "warn", "pass", "pass"]
