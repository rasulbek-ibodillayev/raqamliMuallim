"""Shablon generator: kichik mavzuda foydalanuvchiga yangi savol qolmaganda parametrli savol tuzib, bankka qo'shadi.

- Shablonlar — question_templates.py; kichik mavzuga subtopics.generators orqali bog'lanadi.
- Javob kod bilan hisoblanadi, shuning uchun savol darhol approved (source=template) va keyin hammaga tushadi:
  generator faqat eng ko'p test topshirgan foydalanuvchi bankni tugatganda yangi savol qo'shadi.
- Bir xil parametrli savol bitta bo'ladi (questions.sig). Arxivlangani ham qayta tuzilmaydi.
"""
import random
from collections import Counter

from sqlalchemy import func, select

from ..extensions import db
from ..models import Question, QuestionVersion, Subtopic
from .question_templates import TEMPLATES

CAPACITY = 10               # bitta test uchun bitta kichik mavzudan ko'pi bilan shuncha yangi savol rejalashtiriladi
ROUNDS, BATCH = 4, 8
_rng = random.SystemRandom()


def matching(names, difficulty: str | None = None, types=None) -> list[str]:
    """Shu daraja va turga mos shablonlar nomi."""
    return [n for n in names or [] if n in TEMPLATES
            and (difficulty is None or difficulty in TEMPLATES[n].levels)
            and (not types or TEMPLATES[n].type in types)]


def capacity(names, difficulty: str | None = None, types=None) -> int:
    return CAPACITY if matching(names, difficulty, types) else 0


def _candidates(names: list[str], difficulty: str | None, n: int) -> dict[str, tuple]:
    out = {}
    for _ in range(n):
        t = TEMPLATES[_rng.choice(names)]
        level = difficulty or _rng.choice(t.levels)
        try:
            made = t.fn(_rng, level)
        except ValueError:                       # tasodifiy parametrlar yaroqsiz chiqdi
            continue
        out.setdefault(f"{t.name}:{made.key}", (t, level, made))
    return out


def make(subtopic_id: int, n: int, difficulty: str | None = None, types=None) -> list[Question]:
    """n tagacha yangi savol tuzadi va bankka qo'shadi (commit qilmaydi). Shablon yo'q yoki tugagan bo'lsa kamroq."""
    names = matching(db.session.scalar(select(Subtopic.generators).where(Subtopic.id == subtopic_id)), difficulty, types)
    if not names or n <= 0:
        return []
    # Bir vaqtda ikki so'rov bir xil savol tuzmasin (tranzaksiya oxirigacha)
    db.session.execute(select(func.pg_advisory_xact_lock(7, 0)))
    made: list[Question] = []
    tried: set[str] = set()
    used: Counter[str] = Counter()
    for _ in range(ROUNDS):
        cand = {s: c for s, c in _candidates(names, difficulty, BATCH * n).items() if s not in tried}
        tried |= cand.keys()
        taken = set(db.session.scalars(select(Question.sig).where(Question.sig.in_(cand)))) if cand else set()
        free = [s for s in cand if s not in taken]
        while free and len(made) < n:                # navbat bilan: bitta testda shablonlar har xil bo'lsin
            sig = min(free, key=lambda s: used[s.split(":")[0]])
            free.remove(sig)
            t, level, m = cand[sig]
            used[t.name] += 1
            made.append(Question(subtopic_id=subtopic_id, type=t.type, difficulty=level, text=m.text, data=m.data,
                                 answer=m.answer, explanation=m.why, source="template", status="approved",
                                 version=1, time_limit_s=t.seconds, sig=sig))
        if len(made) >= n:
            break
    db.session.add_all(made)
    db.session.flush()
    db.session.add_all([QuestionVersion(question_id=q.id, version=1, change_note="template") for q in made])
    db.session.flush()
    return made
