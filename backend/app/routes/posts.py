from datetime import UTC, datetime
from pathlib import Path
from shutil import copyfileobj
from uuid import uuid4

from typing import Any

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile

from app.auth import require_user
from app.config import social_account_label
from app.media import create_instagram_image
from app.social.analytics import fetch_post_metrics
from app.social.publisher import publish_post
from app.storage import UPLOADS_DIR, append_post, read_posts, save_post_stats
from app.validation import validate_post_payload

router = APIRouter(prefix="/api/posts", tags=["posts"])


@router.get("")
def get_posts(_: dict = Depends(require_user)) -> dict:
    return {"posts": read_posts()}


@router.post("/{post_id}/metrics")
async def refresh_post_metrics(
    post_id: str,
    body: dict[str, Any] | None = Body(default=None),
    _: dict = Depends(require_user),
) -> dict:
    post = next((item for item in read_posts() if item.get("id") == post_id), None)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found.")

    selected_platforms = body.get("platforms") if isinstance(body, dict) else None
    if not isinstance(selected_platforms, list):
        selected_platforms = None

    selected_platforms = [
        platform
        for platform in selected_platforms or post.get("platforms", [])
        if isinstance(platform, str)
    ]
    metrics = await fetch_post_metrics(post, selected_platforms)

    return {"post": save_post_stats(post, metrics)}


@router.post("", status_code=201)
async def create_post(
    _: dict = Depends(require_user),
    caption: str | None = Form(default=""),
    textOnly: bool = Form(default=False),
    platforms: str | None = Form(default="[]"),
    scheduleMode: str | None = Form(default="instant"),
    scheduledAt: str | None = Form(default=""),
    account: str | None = Form(default=""),
    media: UploadFile | None = File(default=None),
) -> dict:
    errors, value = validate_post_payload(
        caption,
        textOnly,
        platforms,
        media,
        scheduleMode,
        scheduledAt,
        account,
    )
    if errors:
        raise HTTPException(status_code=400, detail=errors)

    media_data = None
    media_paths = []
    if media is not None:
        extension = Path(media.filename or "").suffix
        filename = f"{uuid4()}{extension}"
        destination = UPLOADS_DIR / filename
        media_paths.append(destination)

        with destination.open("wb") as output_file:
            copyfileobj(media.file, output_file)

        media_data = {
            "originalName": media.filename,
            "filename": filename,
            "mimeType": media.content_type,
            "size": destination.stat().st_size,
            "url": f"/uploads/{filename}",
        }
        if "instagram" in value["platforms"] and (media.content_type or "").startswith("image/"):
            instagram_media = create_instagram_image(destination, media.filename or filename)
            if instagram_media is not None:
                media_paths.append(UPLOADS_DIR / instagram_media["filename"])
                media_data["instagram"] = instagram_media

    base_post = {
        "id": str(uuid4()),
        "caption": value["caption"],
        "platforms": value["platforms"],
        "textOnly": value["textOnly"],
        "media": media_data,
        "status": "scheduled" if value["scheduleMode"] == "scheduled" else "publishing",
        "scheduledAt": value["scheduledAt"],
        "createdAt": datetime.now(UTC).isoformat(),
    }
    posts = [
        {
            **base_post,
            "id": str(uuid4()),
            "account": account,
            "accountLabel": social_account_label(account),
        }
        for account in value["accounts"]
    ]

    if value["scheduleMode"] == "scheduled":
        scheduled_posts = [
            append_post(
                {
                    **post,
                    "status": "scheduled",
                    "results": [
                        {
                            "platform": platform,
                            "status": "scheduled",
                            "message": f"Scheduled for {value['scheduledAt']}.",
                        }
                        for platform in post["platforms"]
                    ],
                }
            )
            for post in posts
        ]
        return {"post": scheduled_posts[0], "posts": scheduled_posts}

    saved_posts = []
    all_failed_results = []
    all_published_results = []
    for post in posts:
        results = await publish_post(post)
        failed_results = [result for result in results if result["status"] != "published"]
        published_results = [result for result in results if result["status"] == "published"]
        all_failed_results.extend(
            [
                {**result, "account": post["account"], "accountLabel": post["accountLabel"]}
                for result in failed_results
            ]
        )
        all_published_results.extend(published_results)
        if published_results:
            saved_posts.append(
                append_post(
                    {
                        **post,
                        "status": "partial_failed" if failed_results else "published",
                        "publishedAt": datetime.now(UTC).isoformat(),
                        "results": results,
                    }
                )
            )

    if all_failed_results and not all_published_results:
        for media_path in media_paths:
            if media_path.exists():
                media_path.unlink()

    if all_failed_results:
        raise HTTPException(
            status_code=502,
            detail={
                "post": saved_posts[0] if saved_posts else None,
                "posts": saved_posts,
                "errors": [
                    f"{result['accountLabel']} {result['platform']}: {result.get('message', 'Publish failed.')}"
                    for result in all_failed_results
                ],
            },
        )

    return {"post": saved_posts[0], "posts": saved_posts}
