"""Google orqali kirish: OAuth 2.0 / OpenID Connect (authorization code + PKCE), qo'shimcha kutubxonasiz.

Sozlama: GOOGLE_CLIENT_ID va GOOGLE_CLIENT_SECRET (.env). Google Cloud Console'da ruxsat etilgan qaytish manzili:
https://<domen>/kirish/google/qaytish. So'raladigan ma'lumot: openid, email, profile (ism).

id_token imzosi alohida tekshirilmaydi: u brauzerdan emas, to'g'ridan-to'g'ri Google token manzilidan TLS orqali olinadi
(OpenID Connect Core 3.1.3.7, 6-band). Kim bergani, kim uchun, muddati, nonce va email tasdig'i tekshiriladi.
"""
import base64
import hashlib
import json
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
ISSUERS = ("https://accounts.google.com", "accounts.google.com")
TIMEOUT = 10


class GoogleError(Exception):
    """Google bilan bog'lanib bo'lmadi yoki javob tekshiruvdan o'tmadi."""


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def begin(client_id: str, redirect_uri: str) -> tuple[str, dict]:
    """(Google manzili, sessiyada saqlanadigan bir martalik qiymatlar)."""
    flow = {"state": secrets.token_urlsafe(24), "nonce": secrets.token_urlsafe(24), "verifier": secrets.token_urlsafe(48)}
    params = {"client_id": client_id, "redirect_uri": redirect_uri, "response_type": "code", "scope": "openid email profile",
              "state": flow["state"], "nonce": flow["nonce"], "prompt": "select_account",
              "code_challenge": _b64(hashlib.sha256(flow["verifier"].encode()).digest()), "code_challenge_method": "S256"}
    return f"{AUTH_URL}?{urllib.parse.urlencode(params)}", flow


def _post(data: dict) -> dict:
    req = urllib.request.Request(TOKEN_URL, data=urllib.parse.urlencode(data).encode(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.load(resp)
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        raise GoogleError(f"token: {e}") from e


def _claims(id_token: str) -> dict:
    try:
        body = id_token.split(".")[1]
        return json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
    except (AttributeError, IndexError, ValueError) as e:
        raise GoogleError("id_token o'qilmadi") from e


def finish(client_id: str, client_secret: str, redirect_uri: str, code: str, flow: dict) -> dict:
    """Kodni almashtiradi va tekshiradi. Natija: {"sub", "email", "first", "last"}."""
    tok = _post({"client_id": client_id, "client_secret": client_secret, "code": code, "code_verifier": flow["verifier"],
                 "redirect_uri": redirect_uri, "grant_type": "authorization_code"})
    c = _claims(tok.get("id_token"))
    if c.get("iss") not in ISSUERS or c.get("aud") != client_id:
        raise GoogleError("iss/aud mos emas")
    if not isinstance(c.get("exp"), (int, float)) or c["exp"] < time.time() - 60:
        raise GoogleError("id_token muddati o'tgan")
    if not secrets.compare_digest(str(c.get("nonce", "")), flow["nonce"]):
        raise GoogleError("nonce mos emas")
    if not c.get("sub") or not c.get("email") or c.get("email_verified") not in (True, "true"):
        raise GoogleError("email tasdiqlanmagan")
    return {"sub": str(c["sub"]), "email": c["email"].strip().lower(),
            "first": (c.get("given_name") or "").strip()[:80], "last": (c.get("family_name") or "").strip()[:80]}
