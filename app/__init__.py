"""raqamliMuallim — Flask ilova fabrikasi.

Ekranlar hozircha namunaviy ma'lumotlar (mock.py) bilan ishlaydi.
Ma'lumotlar bazasi modellari: app/models (TZ 23-bo'lim), migratsiyalar: migrations/.
"""
import os

from flask import Flask

DEFAULT_DB = "postgresql+psycopg://raqamli:raqamli@localhost:5432/raqamli"  # docker-compose.yml dagi db


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", DEFAULT_DB)
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
    # /ekranlar va /_rol/<rol> — faqat ishlab chiqishda (debug rejimi yoki RM_DEV_TOOLS=1)
    app.config["DEV_TOOLS"] = os.environ.get("RM_DEV_TOOLS") == "1"
    # Google orqali kirish (services/google_auth.py); bo'sh bo'lsa — ulanmagan
    app.config["GOOGLE_CLIENT_ID"] = os.environ.get("GOOGLE_CLIENT_ID")
    app.config["GOOGLE_CLIENT_SECRET"] = os.environ.get("GOOGLE_CLIENT_SECRET")
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["REMEMBER_COOKIE_SAMESITE"] = "Lax"
    app.config["REMEMBER_COOKIE_HTTPONLY"] = True
    app.config.update(config or {})

    from .extensions import db, login_manager
    from . import models  # noqa: F401 — Alembic barcha jadvallarni ko'rishi uchun

    db.init_app(app)
    if os.environ.get("FLASK_RUN_FROM_CLI") == "true":      # `flask db …`; server worker'iga kerak emas (12 MB RAM)
        from flask_migrate import Migrate
        Migrate(app, db, compare_type=True)

    login_manager.init_app(app)
    # "basic": telefonda IP tez-tez almashadi, "strong" esa bunda foydalanuvchini chiqarib yuborardi
    login_manager.session_protection = "basic"

    @login_manager.user_loader
    def load_user(user_id):
        from .models.users import User
        user = db.session.get(User, int(user_id)) if user_id.isdigit() and len(user_id) < 19 else None
        return user if user is not None and user.is_active else None      # bloklangan akkaunt ochiq sessiyada ham chiqadi

    from . import cli
    cli.init_app(app)

    # CSRF: barcha POST so'rovlar (formalar — yashirin maydon, fetch — X-CSRFToken sarlavhasi)
    from flask_wtf.csrf import CSRFProtect
    CSRFProtect(app)

    from . import i18n, roles
    i18n.init_app(app)
    roles.init_app(app)

    from .views import auth, user, test, expert, admin, meta, api

    for bp in (meta.bp, auth.bp, user.bp, test.bp, expert.bp, admin.bp, api.bp):
        app.register_blueprint(bp)

    from flask import jsonify, render_template, request
    from werkzeug.exceptions import HTTPException

    def wants_json() -> bool:
        return request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json"

    @app.errorhandler(HTTPException)
    def http_error(e):
        if wants_json():
            return jsonify(ok=False, error=e.description), e.code
        code = e.code if e.code in (400, 403, 404) else 500
        return render_template("errors/error.html", code=code), e.code

    @app.errorhandler(Exception)
    def server_error(e):
        app.logger.exception(e)
        if wants_json():
            return jsonify(ok=False, error="Server xatosi"), 500
        return render_template("errors/error.html", code=500), 500

    # Content-Security-Policy: sahifada faqat o'z fayllarimiz va nonce'li inline skriptlar ishlaydi.
    # 'unsafe-eval' — Alpine.js ifodalari (x-data, @click) uchun shart; inline onclick/onchange taqiqlangan,
    # ular o'rniga data-* atributlari ishlatiladi (static/js/core.js). style-src 'unsafe-inline' — style="" atributlari.
    import secrets
    from flask import g

    @app.before_request
    def daily_activity():
        from flask_login import current_user
        if request.endpoint in (None, "static", "meta.service_worker") or not current_user.is_authenticated:
            return
        from .services.activity import touch
        touch(current_user, request.headers.get("User-Agent", ""), request.cookies.get("rm_pwa") == "1")

    @app.before_request
    def make_nonce():
        g.csp_nonce = secrets.token_urlsafe(16)

    @app.context_processor
    def inject_nonce():
        return {"csp_nonce": g.get("csp_nonce", "")}

    @app.after_request
    def security_headers(resp):
        if resp.mimetype == "text/html" and g.get("csp_nonce"):
            resp.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                f"script-src 'self' 'nonce-{g.csp_nonce}' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; "
                "connect-src 'self'; media-src 'self' blob:; worker-src 'self'; manifest-src 'self'; "
                "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'self'")
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return resp

    from . import mock
    from .services import settings as conf

    from flask import get_template_attribute

    ui_macros = ("icon", "badge", "status_dot", "status_badge", "progress", "pct_color", "ring",
                 "code", "spark", "page_head", "back", "composer", "field_error", "objection_btn", "csrf", "eye", "no_autofill")

    @app.context_processor
    def inject_globals():
        # _ui.html makroslari barcha shablonlarda importsiz ishlaydi
        ui = {name: get_template_attribute("_ui.html", name) for name in ui_macros}
        # errors/form — forma xatolari va kiritilgan qiymatlar (forms.respond beradi), standart: bo'sh
        from .views.account import with_user
        from .views.test import TYPE_SLUGS
        # me / staff_of — kirgan foydalanuvchining ismi va aloqasi, qolgani hozircha mock'dan
        return {"errors": {}, "form": {}, "me": with_user(mock.ME), "test_slug": {v: k for k, v in TYPE_SLUGS.items()}, "nav": mock.NAV, "notifications": _notifications,
                "search_index": _search_index, "staff_of": lambda r: with_user(mock.STAFF.get(r, {})), "learner_meta": _learner_meta, "conf": conf.get, **ui}

    def _notifications():
        """Qo'ng'iroqcha (faqat o'qituvchi sahifalarida chaqiriladi)."""
        from flask_login import current_user
        from .services import notify
        return notify.list_for(current_user) if current_user.is_authenticated and current_user.role == "user" else []

    def _learner_meta():
        """O'qituvchi sahifalari uchun: foydalanuvchi va joriy mavzu id'si (0 — hamma mavzu o'zlashtirilgan)."""
        from flask_login import current_user
        if not current_user.is_authenticated or current_user.role != "user":
            return None
        from .services.test_builder import current_topic
        return {"uid": current_user.id, "topic": current_topic(current_user.id) or 0}

    def _search_index():
        """Tezkor qidiruv (Ctrl+K) uchun sahifalar va mavzular ro'yxati."""
        from flask import url_for
        from flask_babel import gettext as tr
        # Guruh nomlari tanlangan tilda: learner.js ham shu matnni rmT("sections") orqali oladi
        sec, top = tr("Bo‘limlar"), tr("Mavzular")
        items = [{"g": sec, "t": str(label), "u": url_for(e), "i": ic} for e, label, ic, _ in mock.NAV["user"]]
        for _, group in mock.NAV["user_groups"]:
            items += [{"g": sec, "t": str(label), "u": url_for(e), "i": ic} for e, label, ic in group]
        items += [{"g": sec, "t": tr(label), "u": url_for(e), "i": ic} for e, label, ic in [
            ("user.profile", "Profil va sozlamalar", "user"), ("user.optional", "Ixtiyoriy test", "settings"),
            ("user.diagnostic", "Diagnostika", "target")]]
        from .services.catalog import topic_titles
        items += [{"g": top, "t": t["name"], "s": t["section"], "u": url_for("user.topic", topic_id=t["id"]), "i": "book"}
                  for t in topic_titles()]
        return items

    import base64

    from .services import highlight, media
    app.jinja_env.globals.update(media_html=media.of, option_html=media.option, option_text=media.option_text, hl=highlight.highlight, hl_lang=highlight.norm_lang)

    @app.template_filter("b64")
    def b64(value: str) -> str:
        """Oldindan tayyorlangan SVG sxemani <img src="data:..."> uchun (partials/blocks.html)."""
        return base64.b64encode((value or "").encode()).decode()

    return app
