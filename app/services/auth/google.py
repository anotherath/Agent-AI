"""Google OAuth 2.0 Authorization Code + PKCE + ID token verify."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from app.core.config import Settings
from app.core.security import pkce_challenge_s256

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_SCOPES = ("openid", "email", "profile")


@dataclass(frozen=True, slots=True)
class GoogleIdentity:
    sub: str
    email: str
    email_verified: bool
    name: str | None
    picture: str | None


class GoogleOAuthError(Exception):
    """Raised when Google OAuth exchange or ID token verification fails."""


def build_authorize_url(
    *,
    client_id: str,
    redirect_uri: str,
    state: str,
    nonce: str,
    code_verifier: str,
) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(GOOGLE_SCOPES),
        "state": state,
        "nonce": nonce,
        "code_challenge": pkce_challenge_s256(code_verifier),
        "code_challenge_method": "S256",
        "access_type": "online",
        "include_granted_scopes": "true",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def exchange_code_for_tokens(
    *,
    settings: Settings,
    code: str,
    code_verifier: str,
    timeout: float = 15.0,
) -> dict[str, Any]:
    client_id, client_secret, redirect_uri = settings.require_google_oauth()
    data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
        "code_verifier": code_verifier,
    }
    try:
        response = httpx.post(GOOGLE_TOKEN_URL, data=data, timeout=timeout)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise GoogleOAuthError(f"Token exchange failed: {exc}") from exc

    payload = response.json()
    if "id_token" not in payload:
        raise GoogleOAuthError("Google token response missing id_token")
    return payload


def verify_google_id_token(
    *,
    raw_id_token: str,
    client_id: str,
    expected_nonce: str,
) -> GoogleIdentity:
    try:
        claims = google_id_token.verify_oauth2_token(
            raw_id_token,
            google_requests.Request(),
            audience=client_id,
        )
    except ValueError as exc:
        raise GoogleOAuthError(f"Invalid Google ID token: {exc}") from exc

    issuer = claims.get("iss")
    if issuer not in {"accounts.google.com", "https://accounts.google.com"}:
        raise GoogleOAuthError(f"Unexpected ID token issuer: {issuer!r}")

    nonce = claims.get("nonce")
    if not nonce or nonce != expected_nonce:
        raise GoogleOAuthError("ID token nonce mismatch")

    sub = claims.get("sub")
    email = claims.get("email")
    if not sub or not email:
        raise GoogleOAuthError("ID token missing sub or email")

    email_verified = bool(claims.get("email_verified"))
    if not email_verified:
        raise GoogleOAuthError("Google email is not verified")

    return GoogleIdentity(
        sub=str(sub),
        email=str(email).strip().lower(),
        email_verified=email_verified,
        name=(str(claims["name"]) if claims.get("name") else None),
        picture=(str(claims["picture"]) if claims.get("picture") else None),
    )


__all__ = [
    "GoogleIdentity",
    "GoogleOAuthError",
    "build_authorize_url",
    "exchange_code_for_tokens",
    "verify_google_id_token",
]
