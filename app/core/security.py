"""Crypto helpers for opaque session tokens and OAuth PKCE."""

from __future__ import annotations

import base64
import hashlib
import secrets


def new_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def pkce_verifier() -> str:
    return secrets.token_urlsafe(64)


def pkce_challenge_s256(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


__all__ = ["new_token", "sha256_hex", "pkce_verifier", "pkce_challenge_s256"]
