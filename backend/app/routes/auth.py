from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from app.auth import (
    clear_session,
    create_session,
    delete_session_cookie,
    find_user_by_email,
    public_user,
    require_user,
    set_session_cookie,
    user_for_session,
    verify_password,
)
from app.config import SESSION_COOKIE_NAME

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginPayload(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(payload: LoginPayload, response: Response) -> dict:
    user = find_user_by_email(payload.email.strip().lower())
    if user is None or not verify_password(payload.password, user["passwordHash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_session(user["id"])
    set_session_cookie(response, token)
    return {"user": public_user(user)}


@router.get("/me")
def get_me(request: Request) -> dict:
    return {"user": public_user(require_user(request))}


@router.get("/session")
def get_session(request: Request) -> dict:
    user = user_for_session(request.cookies.get(SESSION_COOKIE_NAME))
    return {"user": public_user(user) if user else None}


@router.post("/logout")
def logout(request: Request, response: Response) -> dict:
    clear_session(request.cookies.get(SESSION_COOKIE_NAME))
    delete_session_cookie(response)
    return {"ok": True}
