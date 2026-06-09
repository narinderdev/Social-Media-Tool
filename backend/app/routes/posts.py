from datetime import UTC, datetime
from pathlib import Path
from shutil import copyfileobj
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.auth import require_user
from app.media import create_instagram_image
from app.social.publisher import publish_post
from app.storage import UPLOADS_DIR, append_post, read_posts
from app.validation import validate_post_payload

router = APIRouter(prefix="/api/posts", tags=["posts"])


@router.get("")
def get_posts(_: dict = Depends(require_user)) -> dict:
    return {"posts": read_posts()}


@router.post("", status_code=201)
async def create_post(
    _: dict = Depends(require_user),
    caption: str | None = Form(default=""),
    textOnly: bool = Form(default=False),
    platforms: str | None = Form(default="[]"),
    scheduleMode: str | None = Form(default="instant"),
    scheduledAt: str | None = Form(default=""),
    media: UploadFile | None = File(default=None),
) -> dict:
    errors, value = validate_post_payload(
        caption,
        textOnly,
        platforms,
        media,
        scheduleMode,
        scheduledAt,
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

    post = {
        "id": str(uuid4()),
        "caption": value["caption"],
        "platforms": value["platforms"],
        "textOnly": value["textOnly"],
        "media": media_data,
        "status": "scheduled" if value["scheduleMode"] == "scheduled" else "publishing",
        "scheduledAt": value["scheduledAt"],
        "createdAt": datetime.now(UTC).isoformat(),
    }

    if value["scheduleMode"] == "scheduled":
        scheduled_post = append_post(
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
        return {"post": scheduled_post}

    results = await publish_post(post)
    failed_results = [result for result in results if result["status"] != "published"]
    published_results = [result for result in results if result["status"] == "published"]
    saved_post = None
    if published_results:
        saved_post = append_post(
            {
                **post,
                "status": "partial_failed" if failed_results else "published",
                "publishedAt": datetime.now(UTC).isoformat(),
                "results": results,
            }
        )

    if failed_results and not published_results:
        for media_path in media_paths:
            if media_path.exists():
                media_path.unlink()

    if failed_results:
        raise HTTPException(
            status_code=502,
            detail={
                "post": saved_post,
                "errors": [
                    f"{result['platform']}: {result.get('message', 'Publish failed.')}"
                    for result in failed_results
                ],
            },
        )

    return {"post": saved_post}
