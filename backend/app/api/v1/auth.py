from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.deps import get_current_user
from app.core.rate_limit import FailureLimiter, client_ip
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models.user import User
from app.schemas.auth import Token, UserOut
from app.services import audit

router = APIRouter()

_settings = get_settings()
login_limiter = FailureLimiter(_settings.login_max_failures, _settings.login_window_seconds)
_DUMMY_HASH = hash_password("timing-equalizer")


def _set_auth_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    if not settings.auth_use_httponly_cookie:
        return
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )


def _clear_auth_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(key=settings.auth_cookie_name, path="/")


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    response: Response,
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:
    email = form.username.strip().lower()
    ip = client_ip(request)
    keys = (f"email:{email}", f"ip:{ip}")

    if login_limiter.is_blocked(*keys):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Příliš mnoho neúspěšných pokusů. Zkuste to později.",
        )

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    password_ok = verify_password(form.password, user.hashed_password if user else _DUMMY_HASH)

    if not user or not password_ok or not user.is_active:
        login_limiter.record_failure(*keys)
        await audit.log_audit(db, user_id=None, action="auth.login_failed", payload={"ip": ip})
        await db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Špatný e-mail nebo heslo")

    login_limiter.reset(*keys)
    await audit.log_audit(db, user_id=user.id, action="auth.login", payload={"ip": ip})
    await db.commit()
    token = create_access_token(user.email)
    _set_auth_cookie(response, token)
    settings = get_settings()
    if settings.auth_use_httponly_cookie:
        return Token(access_token="")
    return Token(access_token=token)


@router.post("/logout", status_code=204)
async def logout(response: Response) -> None:
    _clear_auth_cookie(response)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> User:
    return user
