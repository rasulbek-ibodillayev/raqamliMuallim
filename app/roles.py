"""Rollar va huquqlar.

| Bo'lim                         | user | expert | admin |
|--------------------------------|------|--------|-------|
| O'qituvchi paneli (/app, /test)|  ✓   |        |       |
| Ekspert paneli (/ekspert)      |      |   ✓    |       |
| Admin paneli (/admin)          |      |        |   ✓   |
| Kirish, maxfiylik, /s/<raqam>  | hamma (ommaviy)       |

Har bir rol faqat o'z paneliga kiradi: admin kontentni tahrirlamaydi (bu ekspert vazifasi),
ekspert foydalanuvchilar ma'lumotini ko'rmaydi, o'qituvchi panellarga kira olmaydi.

Hozircha rol sessiyada saqlanadi (namuna). Kirishda: login'da "admin" bo'lsa — admin, "ekspert" bo'lsa — ekspert,
boshqa holda — o'qituvchi. /ekranlar sahifasi esa /_rol/<rol> orqali rolni almashtirib ochadi.
Backendda: users.role + Flask-Login, shu jadval o'zgarmaydi.
"""
from flask import abort, request, session

ROLES = ("user", "expert", "admin")
REQUIRED = {"user": "user", "test": "user", "api": "user", "expert": "expert", "admin": "admin"}
HOME = {"user": "user.home", "expert": "expert.queue", "admin": "admin.stats"}
LABEL = {"user": "O‘qituvchi", "expert": "Ekspert", "admin": "Administrator"}


def current_role() -> str:
    role = session.get("role")
    return role if role in ROLES else "user"


def role_from_login(login: str) -> str:
    v = (login or "").lower()
    return "admin" if "admin" in v else ("expert" if "ekspert" in v or "expert" in v else "user")


def init_app(app):
    @app.before_request
    def enforce_role():
        need = REQUIRED.get(request.blueprint or "")
        if need and current_role() != need:
            abort(403)

    @app.context_processor
    def inject_role():
        from flask import url_for
        role = current_role()
        return {"role": role, "role_label": LABEL[role], "home_url": url_for(HOME[role])}
