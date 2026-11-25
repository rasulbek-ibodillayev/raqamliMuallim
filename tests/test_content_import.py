"""Kontentni JSON'dan yuklash: tekshiruv, takrorlanmaslik, test yig'ish bilan birga ishlashi."""
import copy
import json

import pytest
from sqlalchemy import func, select

from app.cli import SEED_CONTENT, demo_user
from app.extensions import db
from app.models import ContentBlock, Question, QuestionVersion, Subtopic, Topic
from app.services import attempts
from app.services.content_import import ContentError, check_question, load

SEED = json.loads(SEED_CONTENT.read_text(encoding="utf-8"))

# Bu testlar o'z kontentini yaratadi: namunaviy kontentsiz boshlanadi (conftest.fresh_content)
pytestmark = pytest.mark.usefixtures("fresh_content")


def _count(model):
    return db.session.scalar(select(func.count()).select_from(model))


def _doc(*questions, **sub):
    return {"course": {"slug": "t", "title": "T"}, "sections": [{"title": "S", "topics": [{"title": "T", "subtopics": [
        {"title": "U", "weight": 1, "questions": list(questions), **sub}]}]}]}


def _q(**kw):
    q = {"type": "single", "difficulty": "easy", "text": "Savol?", "data": {"options": ["a", "b"]}, "answer": {"keys": [0]}}
    q.update(kw)
    return q


def test_seed_loads_and_is_idempotent(app):
    with app.app_context():
        r = load(copy.deepcopy(SEED), status="approved")
        n = r.created["questions"]
        assert n >= 15 and r.created["topics"] >= 10 and r.created["blocks"] >= 12
        assert _count(QuestionVersion) == n                       # har savolning 1-versiyasi bor
        again = load(copy.deepcopy(SEED), status="approved")
        assert again.created == {"sections": 0, "topics": 0, "subtopics": 0, "blocks": 0, "questions": 0}
        assert again.skipped_questions == n and _count(Question) == n


def test_seed_supports_test_assembly(app):
    with app.app_context():
        load(copy.deepcopy(SEED), status="approved")
        topic = db.session.scalar(select(Topic).where(Topic.title == "Python: shart operatorlari"))
        plan = attempts.plan_for_topic(topic.id)
        assert sum(plan.values()) == 4                            # weight: 2 + 1 + 1 (+0)
        attempt = attempts.start_attempt(demo_user("user").id, "topic", plan, topic_id=topic.id)
        assert attempt.total == 4


def test_reload_updates_structure_but_not_questions(app):
    with app.app_context():
        doc = _doc(_q())
        load(doc, status="approved")
        doc["sections"][0]["topics"][0]["subtopics"][0]["weight"] = 3
        doc["sections"][0]["topics"][0]["subtopics"][0]["questions"][0]["explanation"] = "yangi izoh"
        load(doc)
        assert db.session.scalar(select(Subtopic.weight)) == 3
        q = db.session.scalar(select(Question))
        assert q.explanation is None and q.status == "approved"   # mavjud savol jimgina o'zgarmaydi


def test_default_status_is_review(app):
    with app.app_context():
        load(_doc(_q()))
        assert db.session.scalar(select(Question.status)) == "review"
        assert db.session.scalar(select(Question.source)) == "import"


def test_invalid_file_writes_nothing(app):
    with app.app_context():
        doc = _doc(_q(), _q(text="Yana", answer={"keys": [5]}))
        with pytest.raises(ContentError) as e:
            load(doc)
        assert e.value.errors == ["sections[0].topics[0].subtopics[0].questions[1]: "
                                  "answer.keys: 0..1 oralig'idagi takrorlanmas indekslar"]
        assert _count(Question) == 0 and _count(Topic) == 0


def test_duplicate_question_in_file_is_rejected(app):
    with app.app_context():
        with pytest.raises(ContentError) as e:
            load(_doc(_q(), _q()))
        assert "ikki marta" in e.value.errors[0]


def test_same_text_with_different_code_is_two_questions(app):
    with app.app_context():
        a = _q(text="Natija?", data={"code": "print(1)", "options": ["1", "2"]})
        b = _q(text="Natija?", data={"code": "print(2)", "options": ["1", "2"]}, answer={"keys": [1]})
        assert load(_doc(a, b)).created["questions"] == 2


def test_blocks_are_validated_and_hashed(app):
    with app.app_context():
        with pytest.raises(ContentError):
            load(_doc(blocks=[{"kind": "pdf", "data": {}}]))
        load(_doc(blocks=[{"kind": "text", "data": {"body": "a"}}, {"kind": "text", "data": {"body": "a"}}]))
        assert _count(ContentBlock) == 1                          # bir xil blok ikki marta yozilmaydi
        assert len(db.session.scalar(select(ContentBlock.content_hash))) == 64


@pytest.mark.parametrize("q, ok", [
    (_q(), True),
    (_q(type="multiple", answer={"keys": [0, 1]}), True),
    (_q(type="multiple", answer={"keys": [0, 0]}), False),
    (_q(answer={"keys": [0, 1]}), False),                         # single'da bitta javob
    (_q(data={"options": ["a"]}), False),
    (_q(answer={"keys": [True]}), False),
    (_q(type="open", data={}, answer={"value": "45", "accept": ["qirq besh"]}), True),
    (_q(type="open", data={}, answer={"value": " "}), False),
    (_q(type="matching", data={"left": ["a", "b"], "right": ["x", "y"]}, answer={"pairs": [1, 0]}), True),
    (_q(type="matching", data={"left": ["a", "b"], "right": ["x", "y"]}, answer={"pairs": [0, 0]}), False),
    (_q(type="essay"), False),
    (_q(difficulty="oson"), False),
])
def test_question_rules(q, ok):
    assert (check_question(q) == []) is ok
