import json
from datetime import UTC, datetime
from urllib.parse import urlparse

from fastapi import UploadFile

from app.config import PLATFORMS, PUBLIC_API_BASE_URL, SOCIAL_DRY_RUN, missing_required_env

LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0"}


def parse_platforms(value: str | None) -> list[str]:
    if not value:
        return []

    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except json.JSONDecodeError:
        pass

    return [item.strip() for item in value.split(",") if item.strip()]


def is_public_https_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and parsed.hostname not in LOCAL_HOSTS


def validate_post_payload(
    caption: str | None,
    text_only: bool,
    platforms: str | None,
    media: UploadFile | None,
    schedule_mode: str | None = "instant",
    scheduled_at: str | None = "",
) -> tuple[list[str], dict]:
    selected_platforms = list(dict.fromkeys(parse_platforms(platforms)))
    clean_caption = (caption or "").strip()
    clean_schedule_mode = (schedule_mode or "instant").strip().lower()
    parsed_scheduled_at = None
    errors = []

    if clean_schedule_mode not in {"instant", "scheduled"}:
        errors.append("Choose instant post or scheduled post.")

    if not selected_platforms:
        errors.append("Select at least one platform.")

    unsupported = [platform for platform in selected_platforms if platform not in PLATFORMS]
    if unsupported:
        errors.append(f"Unsupported platform: {', '.join(unsupported)}.")

    supported_platforms = [platform for platform in selected_platforms if platform in PLATFORMS]
    if SOCIAL_DRY_RUN and supported_platforms:
        errors.append(
            "Local dry-run posting is disabled. Set SOCIAL_DRY_RUN=false and configure platform API keys."
        )
    elif supported_platforms:
        for platform in supported_platforms:
            missing_env = missing_required_env(platform)
            if missing_env:
                errors.append(
                    f"{PLATFORMS[platform].label} needs keys: {', '.join(missing_env)}."
                )

    if media is None and not clean_caption:
        errors.append("Add media or write text before posting.")

    if text_only and media is not None:
        errors.append("Text-only posts cannot include media.")

    if "instagram" in selected_platforms and media is None:
        errors.append("Instagram posting requires an image or video file.")

    instagram_needs_public_media_url = (
        "instagram" in selected_platforms
        and media is not None
        and not is_public_https_url(PUBLIC_API_BASE_URL)
    )
    if instagram_needs_public_media_url:
        errors.append(
            "Instagram posting needs PUBLIC_API_BASE_URL to be a public HTTPS URL, not localhost."
        )

    content_type = media.content_type if media is not None else ""
    if media is not None and not (
        content_type.startswith("image/") or content_type.startswith("video/")
    ):
        errors.append("Only image and video uploads are supported.")

    if clean_schedule_mode == "scheduled":
        if not scheduled_at:
            errors.append("Choose schedule date and time.")
        else:
            try:
                parsed_scheduled_at = datetime.fromisoformat(scheduled_at)
                if parsed_scheduled_at.tzinfo is None:
                    parsed_scheduled_at = parsed_scheduled_at.astimezone()
                parsed_scheduled_at = parsed_scheduled_at.astimezone(UTC)
                if parsed_scheduled_at <= datetime.now(UTC):
                    errors.append("Schedule date and time must be in the future.")
            except ValueError:
                errors.append("Schedule date and time is invalid.")

    return errors, {
        "caption": clean_caption,
        "platforms": selected_platforms,
        "textOnly": text_only,
        "scheduleMode": clean_schedule_mode,
        "scheduledAt": parsed_scheduled_at.isoformat() if parsed_scheduled_at else None,
    }
