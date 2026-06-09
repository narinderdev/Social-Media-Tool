from dataclasses import dataclass
from os import getenv

from dotenv import load_dotenv

load_dotenv()


def bool_from_env(value: str | None, fallback: bool = False) -> bool:
    if value is None:
        return fallback
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class PlatformConfig:
    label: str
    required_env: tuple[str, ...]


PORT = int(getenv("PORT", "4000"))
BACKEND_HOST = getenv("BACKEND_HOST", "127.0.0.1")
FRONTEND_ORIGIN = getenv("FRONTEND_ORIGIN", "http://localhost:5173")
PUBLIC_API_BASE_URL = getenv("PUBLIC_API_BASE_URL", "http://localhost:4000")
DATABASE_URL = getenv("DATABASE_URL", "")
ADMIN_USER = getenv("ADMIN_USER", "")
ADMIN_PASSWORD = getenv("ADMIN_PASSWORD", "")
SESSION_COOKIE_NAME = getenv("SESSION_COOKIE_NAME", "shared_posts_session")
SOCIAL_DRY_RUN = bool_from_env(getenv("SOCIAL_DRY_RUN"), True)
META_GRAPH_API_VERSION = getenv("META_GRAPH_API_VERSION", "v24.0")
LINKEDIN_API_VERSION = getenv("LINKEDIN_API_VERSION", "202605")


def key_from_label(value: str) -> str:
    return "".join(character.lower() if character.isalnum() else "_" for character in value).strip(
        "_"
    )


def env_account_key(account: str) -> str:
    return key_from_label(account).upper()


def configured_accounts() -> list[str]:
    configured = [
        key_from_label(account)
        for account in getenv("SOCIAL_ACCOUNTS", "").split(",")
        if account.strip()
    ]
    return configured or [key_from_label(getenv("DEFAULT_SOCIAL_ACCOUNT", "glowante"))]


def default_social_account() -> str:
    default_account = key_from_label(getenv("DEFAULT_SOCIAL_ACCOUNT", "glowante"))
    return default_account if default_account in configured_accounts() else configured_accounts()[0]


def social_account_label(account: str) -> str:
    account = key_from_label(account or default_social_account())
    label = getenv(f"SOCIAL_ACCOUNT_{env_account_key(account)}_LABEL")
    if label:
        return label
    return " ".join(part.capitalize() for part in account.split("_")) or "Default account"


def is_supported_account(account: str | None) -> bool:
    return key_from_label(account or "") in configured_accounts()


def account_env(account: str | None, env_name: str) -> str | None:
    account_key = key_from_label(account or default_social_account())
    prefixed_value = getenv(f"SOCIAL_ACCOUNT_{env_account_key(account_key)}_{env_name}")
    if prefixed_value:
        return prefixed_value

    if account_key in {default_social_account(), "default"}:
        return getenv(env_name)

    return None


def visible_env_name(account: str | None, env_name: str) -> str:
    account_key = key_from_label(account or default_social_account())
    if account_key in {default_social_account(), "default"}:
        return env_name
    return f"SOCIAL_ACCOUNT_{env_account_key(account_key)}_{env_name}"

PLATFORMS: dict[str, PlatformConfig] = {
    "instagram": PlatformConfig(
        label="Instagram",
        required_env=("INSTAGRAM_ACCOUNT_ID", "INSTAGRAM_ACCESS_TOKEN"),
    ),
    "facebook": PlatformConfig(
        label="Facebook",
        required_env=("FACEBOOK_PAGE_ID", "FACEBOOK_PAGE_ACCESS_TOKEN"),
    ),
    "linkedin": PlatformConfig(
        label="LinkedIn",
        required_env=("LINKEDIN_ACCESS_TOKEN", "LINKEDIN_AUTHOR_URN"),
    ),
    "twitter": PlatformConfig(
        label="X / Twitter",
        required_env=(
            "TWITTER_API_KEY",
            "TWITTER_API_SECRET",
            "TWITTER_ACCESS_TOKEN",
            "TWITTER_ACCESS_TOKEN_SECRET",
        ),
    ),
}


def platform_status(account: str | None = None) -> list[dict]:
    statuses = []

    for key, platform in PLATFORMS.items():
        missing_env = missing_required_env(key, account)
        statuses.append(
            {
                "key": key,
                "label": platform.label,
                "configured": len(missing_env) == 0,
                "dryRun": SOCIAL_DRY_RUN,
                "missingEnv": missing_env,
            }
        )

    return statuses


def account_status() -> list[dict]:
    return [
        {
            "key": account,
            "label": social_account_label(account),
            "default": account == default_social_account(),
            "platforms": platform_status(account),
        }
        for account in configured_accounts()
    ]


def missing_required_env(platform: str, account: str | None = None) -> list[str]:
    return [
        visible_env_name(account, env_name)
        for env_name in PLATFORMS[platform].required_env
        if not account_env(account, env_name)
    ]
