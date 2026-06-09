from datetime import UTC, datetime
from pathlib import Path
from shutil import copyfileobj
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import FRONTEND_ORIGIN, platform_status
from app.media import create_instagram_image
from app.social.publisher import publish_post
from app.storage import UPLOADS_DIR, append_post, ensure_storage, read_posts
from app.validation import validate_post_payload

ensure_storage()

app = FastAPI(title="Shared Posts API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/platforms")
def get_platforms() -> dict:
    return {"platforms": platform_status()}


@app.get("/api/posts")
def get_posts() -> dict:
    return {"posts": read_posts()}


@app.post("/api/posts", status_code=201)
async def create_post(
    caption: str | None = Form(default=""),
    textOnly: bool = Form(default=False),
    platforms: str | None = Form(default="[]"),
    media: UploadFile | None = File(default=None),
) -> dict:
    errors, value = validate_post_payload(caption, textOnly, platforms, media)
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
        "createdAt": datetime.now(UTC).isoformat(),
    }

    results = await publish_post(post)
    failed_results = [result for result in results if result["status"] != "published"]
    if failed_results:
        for media_path in media_paths:
            if media_path.exists():
                media_path.unlink()

        raise HTTPException(
            status_code=502,
            detail=[
                f"{result['platform']}: {result.get('message', 'Publish failed.')}"
                for result in failed_results
            ],
        )

    saved_post = append_post({**post, "results": results})

    return {"post": saved_post}
