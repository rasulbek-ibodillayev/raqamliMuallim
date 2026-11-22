"""Pytest sozlamalari: ilova, test bazasi, mijoz va rol bilan kirish yordamchisi.

Testlar alohida PostgreSQL bazasida ishlaydi (TEST_DATABASE_URL, standart: docker-compose'dagi raqamli_test).
Jadvallar sessiya boshida yaratiladi, har bir testdan keyin barcha jadvallar tozalanadi.
"""
import os

import pytest
from sqlalchemy import text

from app import create_app
from app.extensions import db

JSON = {"Accept": "application/json"}
TEST_DB = os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg://raqamli:raqamli@localhost:5432/raqamli_test")
CONFIG = {"TESTING": True, "WTF_CSRF_ENABLED": False, "SECRET_KEY": "test", "DEV_TOOLS": True,
          "SQLALCHEMY_DATABASE_URI": TEST_DB, "PASSWORD_HASH_METHOD": "pbkdf2:sha256:1"}


@pytest.fixture(scope="session", autouse=True)
def _schema():
    app = create_app(CONFIG)
    with app.app_context():
        with db.engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        db.drop_all()
        db.create_all()
        yield
        db.engine.dispose()


@pytest.fixture()
def app():
    app = create_app(CONFIG)
    yield app
    with app.app_context():
        db.session.remove()
        # Kichik jadvallarda DELETE TRUNCATE'dan ancha tez (fayl amallari yo'q); bolalar jadvali avval
        with db.engine.begin() as conn:
            for t in reversed(db.metadata.sorted_tables):
                conn.execute(t.delete())
        db.engine.dispose()


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
