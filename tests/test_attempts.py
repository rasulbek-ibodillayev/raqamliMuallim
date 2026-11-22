"""Test yig'ish: savol bir foydalanuvchiga takror berilmaydi, savollar bazada bir joyda turadi."""
import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import func, select

from app.cli import demo_user
from app.extensions import db
from app import models as m
from app.models import (AttemptItem, Course, Question, QuestionVersion, Section, Subtopic, Topic,
                        UserSeenQuestion)
from app.services import attempts as tb

# Bu testlar o'z kontentini yaratadi: namunaviy kontentsiz boshlanadi (conftest.fresh_content)
pytestmark = pytest.mark.usefixtures("fresh_content")


@pytest.fixture()
def ctx(app):
    """Bitta mavzu, ikki kichik mavzu (A: 5 ta savol, B: 3 ta), ikki foydalanuvchi."""
    with app.app_context():
        course = Course(slug="inf", title="Informatika")
        sec = Section(course=course, title="Asoslar")
        topic = Topic(section=sec, title="Algoritmlar", is_published=True)
        a = Subtopic(topic=topic, title="A", position=0, weight=2)
        b = Subtopic(topic=topic, title="B", position=1, weight=1)
        db.session.add_all([course, sec, topic, a, b])
        db.session.flush()
        ids = {"A": [], "B": []}
        for name, sub, n in (("A", a, 5), ("B", b, 3)):
            for i in range(n):
                q = Question(subtopic_id=sub.id, type="single", difficulty="easy", text=f"{name}{i}",
                             answer={"keys": ["a"]}, status="approved")
                db.session.add(q)
                db.session.flush()
                db.session.add(QuestionVersion(question_id=q.id, version=1, snapshot={"text": q.text}))
                ids[name].append(q.id)
        # Tasdiqlanmagan savol hech qachon berilmaydi
        db.session.add(Question(subtopic_id=a.id, type="single", difficulty="easy", text="draft",
                                answer={"keys": ["a"]}, status="draft"))
        u1, u2 = demo_user("user"), demo_user("expert")
        db.session.commit()
        yield {"topic": topic.id, "a": a.id, "b": b.id, "ids": ids, "u1": u1.id, "u2": u2.id}


def _qids(attempt):
    return [i.question_id for i in attempt.items]


def test_plan_uses_subtopic_weight(app, ctx):
    with app.app_context():
        assert tb.plan_for_topic(ctx["topic"]) == {ctx["a"]: 2, ctx["b"]: 1}


def test_no_repeats_until_pool_is_exhausted(app, ctx):
    with app.app_context():
        plan = {ctx["a"]: 2}
        first = tb.start_attempt(ctx["u1"], "topic", plan)
        second = tb.start_attempt(ctx["u1"], "topic", plan)
        assert len(set(_qids(first)) | set(_qids(second))) == 4          # 2 + 2, takrorsiz
        assert first.settings_snapshot["repeated"] == second.settings_snapshot["repeated"] == 0
        third = tb.start_attempt(ctx["u1"], "topic", plan)              # A'da faqat 1 ta yangi savol qolgan
        fresh = set(ctx["ids"]["A"]) - set(_qids(first)) - set(_qids(second))
        assert fresh <= set(_qids(third)) and len(_qids(third)) == 2
        assert third.settings_snapshot["repeated"] == 1


def test_repeats_oldest_seen_first(app, ctx):
    with app.app_context():
        a_ids = ctx["ids"]["A"]
        old, *rest = a_ids
        db.session.add_all([UserSeenQuestion(user_id=ctx["u1"], question_id=q,
                                             seen_on=date.today() - timedelta(days=30 if q == old else 1))
                            for q in a_ids])
        db.session.commit()
        attempt = tb.start_attempt(ctx["u1"], "topic", {ctx["a"]: 1})
        assert _qids(attempt) == [old]
        # Qayta berilgan savol sanasi yangilanadi va navbat oxiriga o'tadi
        assert db.session.get(UserSeenQuestion, (ctx["u1"], old)).seen_on == date.today()


def test_users_are_independent_and_questions_stored_once(app, ctx):
    with app.app_context():
        plan = {ctx["a"]: 5, ctx["b"]: 3}
        tb.start_attempt(ctx["u1"], "topic", plan)
        other = tb.start_attempt(ctx["u2"], "topic", plan)
        assert other.settings_snapshot["repeated"] == 0                    # birinchi foydalanuvchi ta'sir qilmaydi
        assert db.session.scalar(select(func.count()).select_from(Question)) == 9   # savollar ko'paymagan
        assert db.session.scalar(select(func.count()).select_from(AttemptItem)) == 16


def test_items_follow_plan_order_and_skip_drafts(app, ctx):
    with app.app_context():
        attempt = tb.start_attempt(ctx["u1"], "topic", tb.plan_for_topic(ctx["topic"]), topic_id=ctx["topic"])
        subs = [db.session.get(Question, q).subtopic_id for q in _qids(attempt)]
        assert subs == [ctx["a"], ctx["a"], ctx["b"]]
        assert [i.position for i in attempt.items] == [0, 1, 2]
        assert all(i.question_version == 1 for i in attempt.items)
        assert attempt.total == 3 and attempt.topic_id == ctx["topic"]


def test_difficulty_filter(app, ctx):
    with app.app_context():
        assert tb.pick_questions(ctx["u1"], {ctx["a"]: 5}, difficulty="hard") == []
        assert len(tb.pick_questions(ctx["u1"], {ctx["a"]: 5}, difficulty="easy")) == 5


def test_client_uuid_is_idempotent(app, ctx):
    with app.app_context():
        cu = uuid.uuid4()
        first = tb.start_attempt(ctx["u1"], "topic", {ctx["a"]: 2}, client_uuid=cu)
        again = tb.start_attempt(ctx["u1"], "topic", {ctx["a"]: 2}, client_uuid=cu)
        assert again.id == first.id
        assert db.session.scalar(select(func.count()).select_from(m.TestAttempt)) == 1
        with pytest.raises(PermissionError):
            tb.start_attempt(ctx["u2"], "topic", {ctx["a"]: 2}, client_uuid=cu)


def test_score_must_be_percent(app, ctx):
    from sqlalchemy.exc import IntegrityError
    with app.app_context():
        attempt = tb.start_attempt(ctx["u1"], "topic", {ctx["a"]: 1})
        attempt.items[0].score = 101
        with pytest.raises(IntegrityError):
            db.session.commit()
