"""raqamliMuallim — Flask ilova fabrikasi.

Ekranlar hozircha namunaviy ma'lumotlar (mock.py) bilan ishlaydi.
"""
import os

from flask import Flask


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-me")

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

    from flask import get_template_attribute

    ui_macros = ("icon", "badge", "status_dot", "status_badge", "progress", "pct_color", "ring",
                 "code", "spark", "page_head", "back", "composer", "field_error", "csrf", "eye", "no_autofill")

    @app.context_processor
    def inject_globals():
        # _ui.html makroslari barcha shablonlarda importsiz ishlaydi
        ui = {name: get_template_attribute("_ui.html", name) for name in ui_macros}
        # errors/form — forma xatolari va kiritilgan qiymatlar (forms.respond beradi), standart: bo'sh
        from .views.test import TYPE_SLUGS
        return {"errors": {}, "form": {}, "me": mock.ME, "test_slug": {v: k for k, v in TYPE_SLUGS.items()}, "nav": mock.NAV, "notifications": mock.NOTIFICATIONS,
                "search_index": _search_index, "staff_of": lambda r: mock.STAFF.get(r, {}), **ui}

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
        for s in mock.SECTIONS:
            items += [{"g": top, "t": t["name"], "s": s["name"], "u": url_for("user.topic", topic_id=t["id"]), "i": "book"}
                      for t in s["topics"]]
        return items

    return app
