"""raqamliMuallim — Flask ilova fabrikasi.

Hozircha faqat frontend (Jinja2 shablonlar + namunaviy ma'lumotlar).
Backend (ma'lumotlar bazasi, autentifikatsiya, AI) keyingi bosqichda qo'shiladi.
"""
from flask import Flask


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "dev-only-change-me"

    from .views import auth, user, test, expert, admin, meta

    for bp in (meta.bp, auth.bp, user.bp, test.bp, expert.bp, admin.bp):
        app.register_blueprint(bp)

    from flask import render_template
    from werkzeug.exceptions import HTTPException

    @app.errorhandler(HTTPException)
    def http_error(e):
        code = e.code if e.code in (403, 404) else 500
        return render_template("errors/error.html", code=code), e.code

    @app.errorhandler(Exception)
    def server_error(e):
        app.logger.exception(e)
        return render_template("errors/error.html", code=500), 500

    from . import mock

    from flask import get_template_attribute

    ui_macros = ("icon", "badge", "status_dot", "status_badge", "progress", "pct_color", "ring",
                 "code", "spark", "page_head", "back", "composer")

    @app.context_processor
    def inject_globals():
        # _ui.html makroslari barcha shablonlarda importsiz ishlaydi
        ui = {name: get_template_attribute("_ui.html", name) for name in ui_macros}
        return {"me": mock.ME, "nav": mock.NAV, "notifications": mock.NOTIFICATIONS,
                "search_index": _search_index, **ui}

    def _search_index():
        """Tezkor qidiruv (Ctrl+K) uchun sahifalar va mavzular ro'yxati."""
        from flask import url_for
        items = [{"g": "Bo‘limlar", "t": label, "u": url_for(e), "i": ic} for e, label, ic, _ in mock.NAV["user"]]
        for _, group in mock.NAV["user_groups"]:
            items += [{"g": "Bo‘limlar", "t": label, "u": url_for(e), "i": ic} for e, label, ic in group]
        items += [{"g": "Bo‘limlar", "t": label, "u": url_for(e), "i": ic} for e, label, ic in [
            ("user.profile", "Profil va sozlamalar", "user"), ("user.optional", "Ixtiyoriy test", "settings"),
            ("user.diagnostic", "Diagnostika", "target")]]
        for s in mock.SECTIONS:
            items += [{"g": "Mavzular", "t": t["name"], "s": s["name"], "u": url_for("user.topic", topic_id=t["id"]), "i": "book"}
                      for t in s["topics"]]
        return items

    return app
