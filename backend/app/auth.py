import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, Request, Response

from app.config import SESSION_COOKIE_NAME
from app.storage import db_connection

SESSION_DAYS = 7


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected_hash = password_hash.split("$", 3)
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    actual_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        int(iterations),
    ).hex()
    return hmac.compare_digest(actual_hash, expected_hash)


def find_user_by_email(email: str) -> dict | None:
    with db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, email, password_hash, role FROM users WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()

    if not row:
        return None

    return {
        "id": row[0],
        "email": row[1],
        "passwordHash": row[2],
        "role": row[3],
    }


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(48)
    expires_at = datetime.now(UTC) + timedelta(days=SESSION_DAYS)

    with db_connection() as connection:
        connection.execute("DELETE FROM sessions WHERE expires_at <= now()")
        connection.execute(
            """
            INSERT INTO sessions (token, user_id, expires_at)
            VALUES (%s, %s, %s)
            """,
            (token, user_id, expires_at),
        )

    return token


def clear_session(token: str | None) -> None:
    if not token:
        return

    with db_connection() as connection:
        connection.execute("DELETE FROM sessions WHERE token = %s", (token,))


def user_for_session(token: str | None) -> dict | None:
    if not token:
        return None

    with db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT users.id, users.email, users.role
                FROM sessions
                JOIN users ON users.id = sessions.user_id
                WHERE sessions.token = %s
                  AND sessions.expires_at > now()
                """,
                (token,),
            )
            row = cursor.fetchone()

    if not row:
        clear_session(token)
        return None

    return {
        "id": row[0],
        "email": row[1],
        "role": row[2],
    }


def public_user(user: dict) -> dict:
    return {
        "email": user["email"],
        "role": user["role"],
    }


def require_user(request: Request) -> dict:
    user = user_for_session(request.cookies.get(SESSION_COOKIE_NAME))
    if user is None:
        raise HTTPException(status_code=401, detail="Login required.")
    return user


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=SESSION_DAYS * 24 * 60 * 60,
        path="/",
    )


def delete_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
