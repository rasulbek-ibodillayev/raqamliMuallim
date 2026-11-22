"""Pytest sozlamalari: ilova, test bazasi, mijoz va rol bilan kirish yordamchisi.

Testlar alohida PostgreSQL bazasida ishlaydi (TEST_DATABASE_URL, standart: docker-compose'dagi raqamli_test).
- Sessiya boshida jadvallar yaratiladi va namunaviy kontent (app/seed/namuna_kontent.json) bir marta yuklanadi.
- Har testdan keyin kontentdan boshqa hamma jadval (foydalanuvchilar, urinishlar, ...) tozalanadi.
- Kontentni o'zi yaratadigan yoki o'zgartiradigan test `fresh_content` fiksturasini oladi: boshida kontent bo'sh,
  oxirida namunaviy kontent qayta tiklanadi.
"""
import copy
import json
import os

import pytest
from sqlalchemy import text

from app import create_app
from app.extensions import db

JSON = {"Accept": "application/json"}
TEST_DB = os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg://raqamli:raqamli@localhost:5432/raqamli_test")
CONFIG = {"TESTING": True, "WTF_CSRF_ENABLED": False, "SECRET_KEY": "test", "DEV_TOOLS": True,
          "SQLALCHEMY_DATABASE_URI": TEST_DB, "PASSWORD_HASH_METHOD": "pbkdf2:sha256:1"}
CONTENT_TABLES = {"courses", "sections", "topics", "subtopics", "topic_prerequisites", "content_blocks",
                  "questions", "question_versions"}


def _delete(tables):
    with db.engine.begin() as conn:
        for t in reversed(db.metadata.sorted_tables):   # bolalar jadvali avval; kichik jadvallarda DELETE TRUNCATE'dan tez
            if t.name in tables:
                conn.execute(t.delete())


def _all_tables():
    return {t.name for t in db.metadata.sorted_tables}


def _load_seed():
    from app.cli import SEED_CONTENT
    from app.services.content_import import load
    load(copy.deepcopy(json.loads(SEED_CONTENT.read_text(encoding="utf-8"))), status="approved")


@pytest.fixture(scope="session", autouse=True)
def _schema():
    app = create_app(CONFIG)
    with app.app_context():
        with db.engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        db.drop_all()
        db.create_all()
        _load_seed()
        yield
        db.engine.dispose()


@pytest.fixture()
def app():
    app = create_app(CONFIG)
    yield app
    with app.app_context():
        db.session.remove()
        _delete(_all_tables() - CONTENT_TABLES)
        db.engine.dispose()


@pytest.fixture()
def fresh_content(app):
    """Kontent jadvallari bo'sh holda boshlanadi; test tugagach namunaviy kontent qayta yuklanadi."""
    with app.app_context():
        _delete(_all_tables())
    yield
    with app.app_context():
        db.session.remove()
        _delete(_all_tables())
        _load_seed()


@pytest.fixture()
def as_role(app):
    """as_role("admin") → shu roldagi namunaviy akkaunt bilan kirgan mijoz (parol: parol1234)."""
    def make(role):
        c = app.test_client()
        assert c.get(f"/_rol/{role}").status_code == 302
        return c
    return make


@pytest.fixture()
def client(as_role):
    """Namunaviy o'qituvchi (Dilnoza Karimova, +998901234567) bilan kirgan mijoz."""
    return as_role("user")


@pytest.fixture()
def guest(app):
    """Tizimga kirmagan mijoz."""
    return app.test_client()
