"""Rollar va huquqlar.

| Bo'lim                         | user | expert | admin |
|--------------------------------|------|--------|-------|
| O'qituvchi paneli (/app, /test)|  ✓   |        |       |
| Ekspert paneli (/ekspert)      |      |   ✓    |       |
| Admin paneli (/admin)          |      |        |   ✓   |
| Kirish, maxfiylik, /s/<raqam>  | hamma (ommaviy)       |

Har bir rol faqat o'z paneliga kiradi: admin kontentni tahrirlamaydi (bu ekspert vazifasi),
ekspert foydalanuvchilar ma'lumotini ko'rmaydi, o'qituvchi panellarga kira olmaydi.

Rol users.role ustunidan olinadi (Flask-Login: current_user). Kirmagan foydalanuvchi yopiq bo'limni ochsa —
kirish sahifasiga yo'naltiriladi (API: 401), boshqa rol bo'lsa — 403.
"""
from flask import abort, jsonify, redirect, request, url_for
from flask_login import current_user

ROLES = ("user", "expert", "admin")
REQUIRED = {"user": "user", "test": "user", "api": "user", "expert": "expert", "admin": "admin"}
HOME = {"user": "user.home", "expert": "expert.questions", "admin": "admin.stats"}
LABEL = {"user": "O‘qituvchi", "expert": "Ekspert", "admin": "Administrator"}


def current_role() -> str | None:
    """Kirgan foydalanuvchining roli; kirmagan bo'lsa None."""
    return current_user.role if current_user.is_authenticated else None


def safe_next(url: str | None) -> str | None:
    """Faqat o'z saytimizdagi nisbiy manzil (ochiq yo'naltirishdan himoya)."""
    return url if url and url.startswith("/") and not url.startswith("//") and "\\" not in url else None


def init_app(app):
    @app.before_request
    def enforce_role():
        need = REQUIRED.get(request.blueprint or "")
        if not need:
            return None
        if not current_user.is_authenticated:
            if request.blueprint == "api" or request.accept_mimetypes.best == "application/json":
                return jsonify(ok=False, error="Avval tizimga kiring"), 401
            nxt = request.full_path.rstrip("?") if request.method == "GET" else None
            return redirect(url_for("auth.login", next=nxt) if nxt else url_for("auth.login"))
        if current_user.role != need:
            abort(403)
        return None

    @app.context_processor
    def inject_role():
        role = current_role()
        return {"role": role, "role_label": LABEL.get(role, ""),
                "home_url": url_for(HOME[role]) if role else url_for("auth.guest")}
