# app/google_oauth.py
# Google OAuth 2.0 authorization-code backend (server-side code exchange + id_token
# verification). The frontend drives the redirect; it sends the one-time code and the
# redirect_uri it used, and this module exchanges the code with Google using the
# confidential client_secret (which never leaves the server) and cryptographically
# verifies the returned id_token before trusting any identity claim.
import json
import os
import time
import urllib.parse
import urllib.request

from dotenv import load_dotenv
from jose import jwt, JWTError

load_dotenv()

# --- Config (from env; NEVER hard-coded). All three must be set for Google login to work.
#   GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET  -> from Zoli's Google Cloud OAuth client.
#   GOOGLE_ALLOWED_REDIRECT_URIS             -> comma-separated allowlist of redirect URIs
#       the frontend may use; each must ALSO be registered on the Google OAuth client.
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_ALLOWED_REDIRECT_URIS = [
    u.strip() for u in os.getenv("GOOGLE_ALLOWED_REDIRECT_URIS", "").split(",") if u.strip()
]

_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
_GOOGLE_ISSUERS = ("accounts.google.com", "https://accounts.google.com")
_HTTP_TIMEOUT = 15

# In-process JWKS cache. Google rotates its signing keys infrequently; we re-fetch when the
# cached set expires or a token's kid is unknown (handled by re-fetch on verify failure).
_jwks_cache = {"keys": None, "exp": 0.0}


class GoogleAuthError(Exception):
    """Any failure in the Google code-exchange / id_token verification path.

    The router maps this to a generic 401 so Google-side internals are never leaked to the
    client.
    """


def is_configured() -> bool:
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and GOOGLE_ALLOWED_REDIRECT_URIS)


def redirect_uri_allowed(redirect_uri: str) -> bool:
    return redirect_uri in GOOGLE_ALLOWED_REDIRECT_URIS


def _http_post_form(url: str, fields: dict) -> dict:
    data = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_get_json(url: str) -> dict:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get_jwks(force: bool = False) -> dict:
    now = time.time()
    if not force and _jwks_cache["keys"] and _jwks_cache["exp"] > now:
        return _jwks_cache["keys"]
    jwks = _http_get_json(_GOOGLE_CERTS_URL)
    _jwks_cache["keys"] = jwks
    _jwks_cache["exp"] = now + 3600.0
    return jwks


def _verify_id_token(id_token: str) -> dict:
    # RS256 verification against Google's published JWKS, with audience (our client_id) and
    # issuer pinned. A stale-key miss triggers exactly one forced JWKS re-fetch.
    last_err = None
    for force in (False, True):
        try:
            return jwt.decode(
                id_token,
                _get_jwks(force=force),
                algorithms=["RS256"],
                audience=GOOGLE_CLIENT_ID,
                issuer=_GOOGLE_ISSUERS,
                options={"verify_at_hash": False},
            )
        except JWTError as e:
            last_err = e
    raise GoogleAuthError("id_token verification failed") from last_err


def exchange_code(code: str, redirect_uri: str) -> dict:
    """Exchange a Google authorization code and return verified identity claims.

    Returns {"email": str, "email_verified": True, "name": str | None}.
    Raises GoogleAuthError on any failure (bad redirect_uri, exchange failure, invalid or
    unverified token).
    """
    if not is_configured():
        raise GoogleAuthError("Google OAuth is not configured on the server")
    if not redirect_uri_allowed(redirect_uri):
        raise GoogleAuthError("redirect_uri is not in the allowed list")

    try:
        token_resp = _http_post_form(
            _GOOGLE_TOKEN_URL,
            {
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
    except Exception as e:
        raise GoogleAuthError("code exchange with Google failed") from e

    id_token = token_resp.get("id_token")
    if not id_token:
        raise GoogleAuthError("Google response did not contain an id_token")

    claims = _verify_id_token(id_token)

    email = claims.get("email")
    if not email:
        raise GoogleAuthError("id_token did not contain an email")
    if not claims.get("email_verified", False):
        raise GoogleAuthError("Google email is not verified")

    return {
        "email": email,
        "email_verified": True,
        "name": claims.get("name") or claims.get("given_name"),
    }
