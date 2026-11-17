"""Pytest sozlamalari: ilova, mijoz va rol bilan kirish yordamchisi."""
import pytest

from app import create_app

JSON = {"Accept": "application/json"}


@pytest.fixture()
def app():
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False, SECRET_KEY="test")
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def as_role(app):
    """as_role("admin") → shu rol bilan kirgan mijoz."""
    def make(role):
        c = app.test_client()
        with c.session_transaction() as s:
            s["role"] = role
        return c
    return make
