"""Unit tests for PKCE / token hashing."""

from __future__ import annotations

from app.core.security import new_token, pkce_challenge_s256, pkce_verifier, sha256_hex


def test_sha256_hex_stable() -> None:
    assert sha256_hex("abc") == sha256_hex("abc")
    assert sha256_hex("abc") != sha256_hex("abcd")
    assert len(sha256_hex("abc")) == 64


def test_pkce_challenge_is_s256() -> None:
    verifier = pkce_verifier()
    challenge = pkce_challenge_s256(verifier)
    assert challenge == pkce_challenge_s256(verifier)
    assert "=" not in challenge
    assert len(challenge) >= 43


def test_new_token_unique() -> None:
    assert new_token() != new_token()
