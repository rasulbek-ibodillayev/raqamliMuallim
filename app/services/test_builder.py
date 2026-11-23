"""Test turlari: qaysi testga qaysi kichik mavzulardan nechta savol tushadi.

| Tur        | Savollar                                                                                   |
|------------|--------------------------------------------------------------------------------------------|
| lesson     | Bitta kichik mavzudan 3 ta; imkon bo'lsa kamida bittasi ko'p javobli yoki moslashtirish (B1) |
| topic      | 2 × darslar soni; avval dars testlarida xato qilingan kichik mavzulardan                     |
| daily      | 5 ta: ko'p xato qilinayotgan kichik mavzulardan, yetmasa o'rganilayotgan mavzulardan         |
| errors     | tanlangan sonda, faqat xato qilingan (hali tuzatilmagan) kichik mavzulardan                  |
| interim    | oxirgi 3 ta o'zlashtirilgan mavzu, har kichik mavzudan har bosqichda 1 ta (bosqichli)        |
| weekly     | o'zlashtirilgan mavzulardan 20 ta (bosqichli)                                                |
| monthly    | o'zlashtirilgan mavzulardan 30 ta (bosqichli)                                                |
| optional   | tanlangan mavzulardan 10/20/30 ta (bosqichli); o'zlashtirish foiziga ta'sir qilmaydi         |
| diagnostic | barcha mavzular, har kichik mavzudan har bosqichda 1 ta (bosqichli)                          |
| final      | xuddi shunday, lekin hamma mavzu o'zlashtirilgach (bosqichli)                                |
| exam       | 35 ta bitta javobli savol, 120 daqiqa                                                        |

Bosqichli test: oson → o'rta → qiyin. Mavzu shu bosqichda < 70% — keyingisiga o'tmaydi; 70–89% — o'tadi, darslarini
takrorlash tavsiya etiladi; ≥ 90% — tavsiyasiz o'tadi (attempts._stage_verdict).
weight = 0 bo'lgan kichik mavzudan savol olinmaydi (dars testidan tashqari).
"""
from dataclasses import dataclass, field

from flask_babel import gettext as _
from sqlalchemy import func, select

from ..extensions import db
from ..models import (ContentBlock, ErrorItem, Question, Section, Subtopic, TestAttempt, Topic, UserTopicProgress)
from . import attempts as at
from .scoring import PASS_MIN

STAGED = {"diagnostic", "interim", "weekly", "optional", "monthly", "final"}
MANDATORY = {"lesson", "topic", "daily", "interim", "monthly", "final"}
MASTERED = ("done", "solid")
DIFFICULTIES = ("easy", "medium", "hard")
LESSON_N, DAILY_N, WEEKLY_N, MONTHLY_N, EXAM_N = 3, 5, 20, 30, 35
EXAM_SECONDS = 120 * 60


class Unavailable(ValueError):
    """Testni hozir tuzib bo'lmaydi (sabab — foydalanuvchiga ko'rsatiladigan matn)."""


@dataclass
class Spec:
    kind: str
    parts: list[list[at.Picked]]                 # bosqichlar (bosqichsiz testda bitta)
    levels: list[str | None] = field(default_factory=lambda: [None])
    topic_id: int | None = None
    subtopic_id: int | None = None
    seconds: int | None = None                   # berilmasa — savollarning time_limit_s yig'indisi
    settings: dict = field(default_factory=dict)


def allocate(n: int, order: list, avail: dict) -> dict:
    """n ta o'rinni order bo'yicha navbat bilan taqsimlaydi; hech biri avail dan oshmaydi. Yetmasa — borincha."""
    got = {k: 0 for k in order}
    left = min(n, sum(avail.get(k, 0) for k in got))
    while left > 0:
        for k in got:
            if left and got[k] < avail.get(k, 0):
                got[k] += 1
                left -= 1
    return {k: v for k, v in got.items() if v}


def _available(*, difficulty=None, types=None) -> dict[int, int]:
    """{kichik mavzu: tasdiqlangan savollar soni}, kontent tartibida (faqat nashr qilingan mavzular, weight > 0)."""
    q = (select(Subtopic.id, func.count(Question.id))
         .join(Question, Question.subtopic_id == Subtopic.id).join(Topic, Topic.id == Subtopic.topic_id)
         .join(Section, Section.id == Topic.section_id)
         .where(Question.status == "approved", Topic.is_published.is_(True), Subtopic.weight > 0)
         .group_by(Subtopic.id, Section.id, Topic.id)
         .order_by(Section.position, Section.id, Topic.position, Topic.id, Subtopic.position, Subtopic.id))
    if difficulty:
        q = q.where(Question.difficulty == difficulty)
    if types:
        q = q.where(Question.type.in_(types))
    return dict(db.session.execute(q).all())


def _subtopics_of(topic_ids) -> set[int]:
    return set(db.session.scalars(select(Subtopic.id).where(Subtopic.topic_id.in_(list(topic_ids)))))


def _mastered(user_id: int, limit: int | None = None) -> list[int]:
    return list(db.session.scalars(
        select(UserTopicProgress.topic_id).where(UserTopicProgress.user_id == user_id,
                                                 UserTopicProgress.status.in_(MASTERED))
        .order_by(UserTopicProgress.updated_at.desc()).limit(limit)))


def weak_subtopics(user_id: int, topic_id: int | None = None) -> list[int]:
    """Tuzatilmagan xatolari bor kichik mavzular, eng ko'p xatodan boshlab."""
    q = (select(ErrorItem.subtopic_id).where(ErrorItem.user_id == user_id, ErrorItem.resolved_at.is_(None))
         .group_by(ErrorItem.subtopic_id).order_by(func.sum(ErrorItem.wrong_count).desc(), ErrorItem.subtopic_id))
    if topic_id:
        q = q.join(Subtopic, Subtopic.id == ErrorItem.subtopic_id).where(Subtopic.topic_id == topic_id)
    return list(db.session.scalars(q))


def current_topic(user_id: int) -> int | None:
    """Rejada hali o'zlashtirilmagan birinchi mavzu (savoli bor). O'quv reja bazaga o'tguncha (5b) shu ishlatiladi."""
    return db.session.scalar(
        select(Topic.id).join(Section, Section.id == Topic.section_id)
        .outerjoin(UserTopicProgress, (UserTopicProgress.topic_id == Topic.id) & (UserTopicProgress.user_id == user_id))
        .where(Topic.is_published.is_(True),
               func.coalesce(UserTopicProgress.status, "none").not_in(MASTERED),
               select(Question.id).join(Subtopic, Subtopic.id == Question.subtopic_id)
               .where(Subtopic.topic_id == Topic.id, Question.status == "approved").exists())
        .order_by(Section.position, Section.id, Topic.position, Topic.id).limit(1))


def current_lesson(user_id: int) -> int | None:
    """Joriy mavzudagi dars testi hali topshirilmagan (< 70%) birinchi kichik mavzu."""
    from .catalog import lesson_scores
    tid = current_topic(user_id)
    if tid is None:
        return None
    scores = lesson_scores(user_id, tid)
    subs = db.session.scalars(
        select(Subtopic.id).where(Subtopic.topic_id == tid, select(Question.id).where(
            Question.subtopic_id == Subtopic.id, Question.status == "approved").exists())
        .order_by(Subtopic.position, Subtopic.id)).all()
    return next((s for s in subs if scores.get(s, 0) < PASS_MIN), subs[0] if subs else None)


def _staged(user_id, subtopics: set[int] | None, *, n: int | None) -> tuple[list, list]:
    """Bosqichlar: n berilsa — jami n ta savol bosqichlarga teng bo'linadi, aks holda har kichik mavzudan 1 ta."""
    avail = {d: {s: c for s, c in _available(difficulty=d).items() if subtopics is None or s in subtopics}
             for d in DIFFICULTIES}
    if n is None:
        plans = {d: {s: 1 for s in a} for d, a in avail.items()}
    else:
        quota = allocate(n, list(DIFFICULTIES), {d: sum(a.values()) for d, a in avail.items()})
        plans = {d: allocate(quota.get(d, 0), list(a), a) for d, a in avail.items()}
    parts, levels = [], []
    for d in DIFFICULTIES:
        picked = at.pick_questions(user_id, plans[d], d)
        if picked:
            parts.append(picked)
            levels.append(d)
    return parts, levels


def _lesson(user_id: int, sid: int) -> list[at.Picked]:
    """3 savol; hammasi bir javobli/ochiq chiqsa, oxirgisi ko'p javobli yoki moslashtirishga almashtiriladi —
    aks holda 70–89% natija chiqishi mumkin emas (B1)."""
    picked = at.pick_questions(user_id, {sid: LESSON_N})
    if picked and not any(p.type in at.PARTIAL_TYPES for p in picked):
        extra = at.pick_questions(user_id, {sid: 1}, types=at.PARTIAL_TYPES)
        if extra:
            # Yangi savollarni saqlab qolamiz: avval ko'rilgani (oxirgi o'rinda) almashtiriladi
            picked = [*picked[:-1], *extra] if len(picked) >= LESSON_N else [*picked, *extra]
    return picked


def build(user_id: int, kind: str, *, topic_id: int | None = None, subtopic_id: int | None = None,
          topic_ids: list[int] | None = None, n: int | None = None) -> Spec:
    """Testni tuzadi (bazaga yozmaydi). Tuzib bo'lmasa — Unavailable."""
    no_questions = _("Bu test uchun hali tasdiqlangan savollar yetarli emas")
    if kind == "lesson":
        sid = subtopic_id or current_lesson(user_id)
        sub = db.session.get(Subtopic, sid) if sid else None
        if sub is None or not sub.topic.is_published:
            raise Unavailable(_("Dars topilmadi"))
        spec = Spec(kind, [_lesson(user_id, sub.id)], topic_id=sub.topic_id, subtopic_id=sub.id)
    elif kind == "topic":
        tid = topic_id or current_topic(user_id)
        topic = db.session.get(Topic, tid) if tid else None
        if topic is None or not topic.is_published:
            raise Unavailable(_("Mavzu topilmadi"))
        mine = _subtopics_of([tid])
        avail = {s: c for s, c in _available().items() if s in mine}
        lessons = db.session.scalar(select(func.count(func.distinct(ContentBlock.subtopic_id)))
                                    .where(ContentBlock.subtopic_id.in_(mine), ContentBlock.is_active.is_(True)))
        weak = [s for s in weak_subtopics(user_id, tid) if s in avail]
        order = weak + [s for s in avail if s not in weak]
        plan = allocate(2 * (lessons or len(avail)), order, avail)
        spec = Spec(kind, [at.pick_questions(user_id, {s: plan[s] for s in avail if s in plan})], topic_id=tid)
    elif kind in ("daily", "errors"):
        avail = _available()
        weak = [s for s in weak_subtopics(user_id) if s in avail]
        if kind == "errors":
            if not weak:
                raise Unavailable(_("Tuzatilmagan xatolar yo‘q — bu test xato qilingan savollardan tuziladi"))
            plan = allocate(n or 10, weak, avail)
        else:
            learning = _subtopics_of(db.session.scalars(select(UserTopicProgress.topic_id)
                                                        .where(UserTopicProgress.user_id == user_id)))
            plan, left = {}, DAILY_N
            for tier in (weak, [s for s in avail if s in learning], list(avail)):
                got = allocate(left, [s for s in tier if s not in plan], avail)
                plan.update(got)
                left -= sum(got.values())
        spec = Spec(kind, [at.pick_questions(user_id, plan)])
    elif kind == "exam":
        avail = _available(types=("single",))
        plan = allocate(EXAM_N, list(avail), avail)
        spec = Spec(kind, [at.pick_questions(user_id, plan, types=("single",))], seconds=EXAM_SECONDS)
    elif kind in STAGED:
        subs = None
        if kind in ("interim", "weekly", "monthly"):
            topics = _mastered(user_id, 3 if kind == "interim" else None)
            if not topics:
                raise Unavailable(_("Hali o‘zlashtirilgan mavzu yo‘q — bu test o‘zlashtirilgan mavzulardan tuziladi"))
            subs = _subtopics_of(topics)
        elif kind == "optional":
            subs = _subtopics_of(topic_ids) if topic_ids else None
        elif kind == "final":
            published = set(db.session.scalars(
                select(Topic.id).where(Topic.is_published.is_(True), select(Question.id)
                                       .join(Subtopic, Subtopic.id == Question.subtopic_id)
                                       .where(Subtopic.topic_id == Topic.id, Question.status == "approved").exists())))
            if published - set(_mastered(user_id)):
                raise Unavailable(_("Yakuniy diagnostika barcha mavzular o‘zlashtirilgach ochiladi"))
        size = {"weekly": WEEKLY_N, "monthly": MONTHLY_N, "optional": n or 20}.get(kind)
        parts, levels = _staged(user_id, subs, n=size)
        spec = Spec(kind, parts, levels, settings={"topic_ids": sorted(topic_ids)} if topic_ids else {})
    else:
        raise Unavailable(_("Test turi noto‘g‘ri"))
    if not any(spec.parts):
        raise Unavailable(no_questions)
    return spec


def get_or_start(user_id: int, kind: str, **params) -> tuple[TestAttempt, bool]:
    """Yakunlanmagan shu test bo'lsa — o'sha, aks holda yangisi. Natija: (urinish, yangimi).

    Majburiy test yakunlanmagan bo'lsa, boshqa majburiy test boshlanmaydi (Unavailable)."""
    # Ikki marta bosilganda ikkita urinish yaratilmasin: shu foydalanuvchi uchun navbat (tranzaksiya oxirigacha)
    db.session.execute(select(func.pg_advisory_xact_lock(6, int(user_id) % 2_147_483_647)))
    if kind == "lesson" and not params.get("subtopic_id"):
        params["subtopic_id"] = current_lesson(user_id)
    if kind == "topic" and not params.get("topic_id"):
        params["topic_id"] = current_topic(user_id)
    for a in unfinished(user_id):
        same = (a.kind == kind and (kind != "lesson" or a.subtopic_id == params.get("subtopic_id"))
                and (kind != "topic" or a.topic_id == params.get("topic_id")))
        if same:
            return a, False
        if kind in MANDATORY and a.kind in MANDATORY:
            raise Unavailable(_("Avval boshlangan majburiy testni yakunlang"))
    spec = build(user_id, kind, **params)
    return at.create(user_id, spec), True


def unfinished(user_id: int) -> list[TestAttempt]:
    return list(db.session.scalars(select(TestAttempt).where(TestAttempt.user_id == user_id,
                                                             TestAttempt.status == "in_progress")
                                   .order_by(TestAttempt.started_at.desc())))
