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
SOCIAL_DRY_RUN = bool_from_env(getenv("SOCIAL_DRY_RUN"), True)
META_GRAPH_API_VERSION = getenv("META_GRAPH_API_VERSION", "v24.0")
LINKEDIN_API_VERSION = getenv("LINKEDIN_API_VERSION", "202605")

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


def platform_status() -> list[dict]:
    statuses = []

    for key, platform in PLATFORMS.items():
        missing_env = missing_required_env(key)
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


def missing_required_env(platform: str) -> list[str]:
    return [env_name for env_name in PLATFORMS[platform].required_env if not getenv(env_name)]
