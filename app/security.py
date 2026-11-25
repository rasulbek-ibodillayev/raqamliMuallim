"""Himoya sozlamalari: maxfiy kalit, cookie'lar, so'rov hajmi, proksi va xavfsizlik sarlavhalari.

Muhit o'zgaruvchilari (.env, run.py o'qiydi):
- SECRET_KEY — serverda shart: usiz ilova ishga tushmaydi (ma'lum kalit bilan istalgan akkauntga cookie yasash mumkin);
- RM_PROXY_HOPS — oldidagi proksilar soni (nginx — 1): IP va https X-Forwarded-* dan olinadi. Proksisiz 0 bo'lsin,
  aks holda mijoz o'z IP'sini soxtalashtira oladi;
- RM_HOSTS — ruxsat etilgan domenlar vergul bilan: soxta Host sarlavhasi bilan havola (parol havolasi) yasab bo'lmasin.
"""
import os
import secrets

from flask import Flask, Request, abort, g, request
from flask.helpers import get_debug_flag
from werkzeug.exceptions import SecurityError

KB, MB = 1024, 1024 * 1024
BODY_MAX, EDITOR_MAX, UPLOAD_MAX = 512 * KB, 2 * MB, 6 * MB      # 6 MB: Excel 5 MB (services/xlsx.py) + forma maydonlari
BODY_LIMITS = {"expert.lesson_save": EDITOR_MAX, **dict.fromkeys(
    ("expert.editor_save", "expert.editor_preview", "expert.excel_import", "expert.lesson_image", "admin.dates_import"), UPLOAD_MAX)}


class LimitedRequest(Request):
    """So'rov hajmi: fayl yuklanadigan manzillarda 6 MB, dars muharririda 2 MB, qolgan hammasida 512 KB."""

    @property
    def max_content_length(self) -> int:
        return BODY_LIMITS.get(self.endpoint or "", BODY_MAX)


def _secret_key(dev: bool) -> str:
    key = os.environ.get("SECRET_KEY", "")
    if key:
        if not dev and len(key) < 32:
            raise RuntimeError("SECRET_KEY kamida 32 belgi bo'lsin: python -c \"import secrets; print(secrets.token_hex(32))\"")
        return key
    if dev:
        return "dev-only-change-me"
    if os.environ.get("FLASK_RUN_FROM_CLI") == "true":
        return secrets.token_hex(32)                # `flask db upgrade` kabi buyruqlarga sessiya kerak emas
    raise RuntimeError("SECRET_KEY berilmagan. .env fayliga yozing (.env.example ga qarang)")


def configure(app: Flask, config: dict) -> None:
    dev = get_debug_flag() or bool(config.get("TESTING"))
    app.config["SECRET_KEY"] = config.get("SECRET_KEY") or _secret_key(dev)
    secure = not dev and not app.config["DEV_TOOLS"]            # ishlab chiqishda http://localhost
    app.config.update(
        MAX_CONTENT_LENGTH=UPLOAD_MAX, SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=secure,
        REMEMBER_COOKIE_SAMESITE="Lax", REMEMBER_COOKIE_HTTPONLY=True, REMEMBER_COOKIE_SECURE=secure,
        # Standart 1 soat edi: 120 daqiqalik attestatsiya testida token eskirib, javoblar serverga yozilmay qolardi.
        # Token baribir sessiyaga bog'langan
        WTF_CSRF_TIME_LIMIT=None)
    app.request_class = LimitedRequest
    hops = int(os.environ.get("RM_PROXY_HOPS") or 0)
    if hops:
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=hops, x_proto=hops)
    app.config["HOSTS"] = [h.strip() for h in os.environ.get("RM_HOSTS", "").split(",") if h.strip()]


def init_app(app: Flask) -> None:
    @app.before_request
    def check_host():
        if app.config["HOSTS"]:
            request.trusted_hosts = app.config["HOSTS"]
            try:
                request.host                        # ruxsat etilmagan bo'lsa SecurityError
            except SecurityError:
                abort(400)

    @app.before_request
    def make_nonce():
        g.csp_nonce = secrets.token_urlsafe(16)

    @app.context_processor
    def inject():
        return {"csp_nonce": g.get("csp_nonce", ""), "is_dev": bool(app.debug or app.config.get("DEV_TOOLS"))}

    # Content-Security-Policy: sahifada faqat o'z fayllarimiz va nonce'li inline skriptlar ishlaydi.
    # 'unsafe-eval' — Alpine.js ifodalari (x-data, @click) uchun shart; inline onclick/onchange taqiqlangan,
    # ular o'rniga data-* atributlari ishlatiladi (static/js/core.js). style-src 'unsafe-inline' — style="" atributlari.
    @app.after_request
    def headers(resp):
        if resp.mimetype == "text/html":
            if g.get("csp_nonce"):
                resp.headers["Content-Security-Policy"] = (
                    "default-src 'self'; "
                    f"script-src 'self' 'nonce-{g.csp_nonce}' 'unsafe-eval'; "
                    "style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; "
                    "connect-src 'self'; media-src 'self' blob:; worker-src 'self'; manifest-src 'self'; "
                    "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'self'")
            resp.headers.setdefault("Permissions-Policy", "camera=(), geolocation=(), payment=(), usb=(), microphone=(self)")
            resp.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
            resp.vary.add("Cookie")                 # CVE-2026-27205: umumiy kesh birovning sahifasini bermasin
        # Panel va kirish sahifalari (shaxsiy ma'lumot, bir martalik havolalar) brauzer keshida qolmasin.
        # /app va /test keshlanadi: oflayn rejim (sw.js) shularga tayanadi
        if request.blueprint in ("auth", "admin", "expert", "api"):
            resp.headers.setdefault("Cache-Control", "no-store")
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        if request.is_secure:
            resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
        return resp
