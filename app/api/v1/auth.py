"""Google OAuth + session endpoints."""

from __future__ import annotations

from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_session_token
from app.core.config import Settings, get_settings
from app.core.cookies import clear_session_cookie, set_session_cookie
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import UserOut
from app.services.auth.google import (
    GoogleOAuthError,
    build_authorize_url,
    exchange_code_for_tokens,
    verify_google_id_token,
)
from app.services.auth.oauth_transactions import (
    consume_oauth_transaction,
    create_oauth_transaction,
)
from app.services.auth.sessions import create_session, revoke_session
from app.services.auth.users import upsert_user_from_google

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    if request.client:
        return request.client.host
    return None


def _error_response(
    settings: Settings,
    *,
    detail: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
) -> RedirectResponse | JSONResponse:
    if settings.auth_error_redirect_url:
        q = urlencode({"error": detail})
        sep = "&" if "?" in settings.auth_error_redirect_url else "?"
        return RedirectResponse(
            url=f"{settings.auth_error_redirect_url}{sep}{q}",
            status_code=status.HTTP_302_FOUND,
        )
    return JSONResponse(
        status_code=status_code,
        content={"status": "error", "detail": detail},
    )


@router.get("/google/login", response_model=None)
def google_login(
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> RedirectResponse:
    try:
        client_id, _, redirect_uri = settings.require_google_oauth()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    tx = create_oauth_transaction(db, settings)
    db.commit()

    url = build_authorize_url(
        client_id=client_id,
        redirect_uri=redirect_uri,
        state=tx.state,
        nonce=tx.nonce,
        code_verifier=tx.code_verifier,
    )
    return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)


@router.get("/google/callback", response_model=None)
def google_callback(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse | JSONResponse:
    if error:
        return _error_response(settings, detail=f"google_oauth_error:{error}")
    if not code or not state:
        return _error_response(settings, detail="missing_code_or_state")

    try:
        client_id, _, _ = settings.require_google_oauth()
        tx = consume_oauth_transaction(db, state)
        token_payload = exchange_code_for_tokens(
            settings=settings,
            code=code,
            code_verifier=tx.code_verifier,
        )
        identity = verify_google_id_token(
            raw_id_token=token_payload["id_token"],
            client_id=client_id,
            expected_nonce=tx.nonce,
        )
        user = upsert_user_from_google(db, identity)
        _, raw_token = create_session(
            db,
            user=user,
            settings=settings,
            ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        return _error_response(settings, detail=str(exc))
    except GoogleOAuthError as exc:
        db.rollback()
        return _error_response(settings, detail=str(exc))
    except Exception:
        db.rollback()
        return _error_response(
            settings,
            detail="login_failed",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if settings.auth_success_redirect_url:
        response: RedirectResponse | JSONResponse = RedirectResponse(
            url=settings.auth_success_redirect_url,
            status_code=status.HTTP_302_FOUND,
        )
    else:
        response = JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "ok",
                "user": UserOut.model_validate(user).model_dump(mode="json"),
            },
        )
    set_session_cookie(response, settings, raw_token)
    return response


@router.post("/logout", response_model=None)
def logout(
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    token: Annotated[str | None, Depends(get_session_token)],
) -> JSONResponse:
    revoke_session(db, token)
    db.commit()
    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "ok", "detail": "logged_out"},
    )
    clear_session_cookie(response, settings)
    return response


@router.get("/me", response_model=UserOut)
def me(user: Annotated[User, Depends(get_current_user)]) -> User:
    return user
