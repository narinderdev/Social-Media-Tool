import hashlib
import json
import secrets
from pathlib import Path
from typing import Any

from app.config import ADMIN_PASSWORD, ADMIN_USER, DATABASE_URL

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
POSTS_FILE = DATA_DIR / "posts.json"


def using_database() -> bool:
    return bool(DATABASE_URL)


def db_connection():
    import psycopg

    return psycopg.connect(DATABASE_URL)


def ensure_posts_table() -> None:
    with db_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS posts (
                id text PRIMARY KEY,
                caption text NOT NULL DEFAULT '',
                platforms jsonb NOT NULL,
                account text NOT NULL DEFAULT 'glowante',
                account_label text NOT NULL DEFAULT 'Glowante',
                text_only boolean NOT NULL DEFAULT false,
                media jsonb,
                results jsonb NOT NULL,
                status text NOT NULL DEFAULT 'published',
                scheduled_at timestamptz,
                created_at timestamptz NOT NULL,
                payload jsonb NOT NULL
            )
            """
        )
        connection.execute("ALTER TABLE posts ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'published'")
        connection.execute("ALTER TABLE posts ADD COLUMN IF NOT EXISTS scheduled_at timestamptz")
        connection.execute("ALTER TABLE posts ADD COLUMN IF NOT EXISTS account text NOT NULL DEFAULT 'glowante'")
        connection.execute("ALTER TABLE posts ADD COLUMN IF NOT EXISTS account_label text NOT NULL DEFAULT 'Glowante'")
        connection.execute(
            """
            UPDATE posts
            SET
                account = COALESCE(NULLIF(payload->>'account', ''), account, 'glowante'),
                account_label = COALESCE(NULLIF(payload->>'accountLabel', ''), account_label, 'Glowante')
            """
        )


def hash_password(password: str) -> str:
    iterations = 260000
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()
    return f"pbkdf2_sha256${iterations}${salt}${password_hash}"


def ensure_auth_tables() -> None:
    with db_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id bigserial PRIMARY KEY,
                email text UNIQUE NOT NULL,
                password_hash text NOT NULL,
                role text NOT NULL DEFAULT 'admin',
                created_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token text PRIMARY KEY,
                user_id bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at timestamptz NOT NULL DEFAULT now(),
                expires_at timestamptz NOT NULL
            )
            """
        )


def seed_admin_user() -> None:
    if not ADMIN_USER or not ADMIN_PASSWORD:
        return

    with db_connection() as connection:
        connection.execute(
            """
            INSERT INTO users (email, password_hash, role)
            VALUES (%s, %s, 'admin')
            ON CONFLICT (email) DO UPDATE SET
                password_hash = EXCLUDED.password_hash,
                role = 'admin'
            """,
            (ADMIN_USER, hash_password(ADMIN_PASSWORD)),
        )


def append_post_to_database(post: dict[str, Any]) -> dict[str, Any]:
    from psycopg.types.json import Jsonb

    with db_connection() as connection:
        connection.execute(
            """
            INSERT INTO posts (
                id,
                caption,
                platforms,
                account,
                account_label,
                text_only,
                media,
                results,
                status,
                scheduled_at,
                created_at,
                payload
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::timestamptz, %s::timestamptz, %s)
            ON CONFLICT (id) DO UPDATE SET
                caption = EXCLUDED.caption,
                platforms = EXCLUDED.platforms,
                account = EXCLUDED.account,
                account_label = EXCLUDED.account_label,
                text_only = EXCLUDED.text_only,
                media = EXCLUDED.media,
                results = EXCLUDED.results,
                status = EXCLUDED.status,
                scheduled_at = EXCLUDED.scheduled_at,
                created_at = EXCLUDED.created_at,
                payload = EXCLUDED.payload
            """,
            (
                post["id"],
                post["caption"],
                Jsonb(post["platforms"]),
                post.get("account", "glowante"),
                post.get("accountLabel", "Glowante"),
                post["textOnly"],
                Jsonb(post.get("media")),
                Jsonb(post["results"]),
                post.get("status", "published"),
                post.get("scheduledAt"),
                post["createdAt"],
                Jsonb(post),
            ),
        )
    return post


def migrate_json_posts_to_database() -> None:
    if not POSTS_FILE.exists():
        return

    posts = json.loads(POSTS_FILE.read_text(encoding="utf-8"))
    for post in posts:
        append_post_to_database(post)


def ensure_storage() -> None:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    if using_database():
        ensure_posts_table()
        ensure_auth_tables()
        seed_admin_user()
        migrate_json_posts_to_database()
        return

    if not POSTS_FILE.exists():
        POSTS_FILE.write_text("[]\n", encoding="utf-8")


def read_posts() -> list[dict[str, Any]]:
    ensure_storage()
    if using_database():
        with db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT payload FROM posts ORDER BY created_at DESC")
                return [row[0] for row in cursor.fetchall()]

    return json.loads(POSTS_FILE.read_text(encoding="utf-8"))


def append_post(post: dict[str, Any]) -> dict[str, Any]:
    if using_database():
        return append_post_to_database(post)

    posts = read_posts()
    posts.insert(0, post)
    POSTS_FILE.write_text(json.dumps(posts, indent=2) + "\n", encoding="utf-8")
    return post


def update_post(post: dict[str, Any]) -> dict[str, Any]:
    if using_database():
        return append_post_to_database(post)

    posts = read_posts()
    next_posts = [post if item["id"] == post["id"] else item for item in posts]
    POSTS_FILE.write_text(json.dumps(next_posts, indent=2) + "\n", encoding="utf-8")
    return post


def read_due_scheduled_posts() -> list[dict[str, Any]]:
    ensure_storage()
    if using_database():
        with db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT payload
                    FROM posts
                    WHERE status = 'scheduled'
                      AND scheduled_at <= now()
                    ORDER BY scheduled_at ASC
                    """
                )
                return [row[0] for row in cursor.fetchall()]

    now = datetime_now_iso()
    return [
        post
        for post in read_posts()
        if post.get("status") == "scheduled" and post.get("scheduledAt", "") <= now
    ]


def datetime_now_iso() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()
