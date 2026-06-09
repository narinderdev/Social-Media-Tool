import asyncio
import base64
import hashlib
import hmac
import json
import mimetypes
import secrets
import time
from os import getenv
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen
from uuid import uuid4

from app.config import (
    LINKEDIN_API_VERSION,
    META_GRAPH_API_VERSION,
    PLATFORMS,
    PUBLIC_API_BASE_URL,
    SOCIAL_DRY_RUN,
    missing_required_env,
)
from app.storage import UPLOADS_DIR

GRAPH_API_BASE_URL = f"https://graph.facebook.com/{META_GRAPH_API_VERSION}"
LINKEDIN_API_BASE_URL = "https://api.linkedin.com/rest"
TWITTER_API_BASE_URL = "https://api.x.com"
TWITTER_UPLOAD_BASE_URL = "https://upload.twitter.com"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0"}


def media_url_for(post: dict[str, Any], platform: str | None = None) -> str | None:
    media = post.get("media")
    if not media:
        return None

    platform_media = media.get(platform) if platform else None
    media_url = platform_media["url"] if platform_media else media["url"]
    return f"{PUBLIC_API_BASE_URL}{media_url}"


def media_path_for(post: dict[str, Any]) -> Path | None:
    media = post.get("media")
    if not media:
        return None
    return UPLOADS_DIR / media["filename"]


def is_public_https_url(value: str | None) -> bool:
    if not value:
        return False

    parsed = urlparse(value)
    return parsed.scheme == "https" and parsed.hostname not in LOCAL_HOSTS


def graph_api_error(error: Exception) -> str:
    if isinstance(error, HTTPError):
        try:
            body = json.loads(error.read().decode("utf-8"))
            return api_error_message(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return str(error.reason)

    if isinstance(error, URLError):
        return str(error.reason)

    return str(error) or "Unknown Meta Graph API error."


def api_error_message(body: Any) -> str:
    if isinstance(body, dict):
        input_errors = body.get("errorDetails", {}).get("inputErrors", [])
        if input_errors:
            description = input_errors[0].get("description")
            if description:
                return str(description)

        errors = body.get("errors")
        if isinstance(errors, list) and errors:
            return api_error_message(errors[0])

        error = body.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if message:
                return str(message)

        for key in ("detail", "message", "description", "title"):
            if body.get(key):
                return str(body[key])

    return "Publish failed."


def graph_post_form(path: str, fields: dict[str, Any]) -> dict[str, Any]:
    data = urlencode({key: value for key, value in fields.items() if value is not None}).encode(
        "utf-8"
    )
    request = Request(
        f"{GRAPH_API_BASE_URL}{path}",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    with urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def graph_post_multipart(
    path: str,
    fields: dict[str, Any],
    file_field: str,
    file_path: Path,
    content_type: str | None,
) -> dict[str, Any]:
    boundary = f"shared-posts-{uuid4().hex}"
    body = bytearray()

    for key, value in fields.items():
        if value is None:
            continue
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"))
        body.extend(str(value).encode("utf-8"))
        body.extend(b"\r\n")

    filename = file_path.name
    guessed_type = content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(
        (
            f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'
            f"Content-Type: {guessed_type}\r\n\r\n"
        ).encode("utf-8")
    )
    body.extend(file_path.read_bytes())
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    request = Request(
        f"{GRAPH_API_BASE_URL}{path}",
        data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )

    with urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def graph_get(path: str, fields: dict[str, Any]) -> dict[str, Any]:
    query = urlencode({key: value for key, value in fields.items() if value is not None})
    request = Request(f"{GRAPH_API_BASE_URL}{path}?{query}", method="GET")

    with urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


async def post_form(path: str, fields: dict[str, Any]) -> dict[str, Any]:
    return await asyncio.to_thread(graph_post_form, path, fields)


async def post_multipart(
    path: str,
    fields: dict[str, Any],
    file_field: str,
    file_path: Path,
    content_type: str | None,
) -> dict[str, Any]:
    return await asyncio.to_thread(
        graph_post_multipart,
        path,
        fields,
        file_field,
        file_path,
        content_type,
    )


async def get_graph(path: str, fields: dict[str, Any]) -> dict[str, Any]:
    return await asyncio.to_thread(graph_get, path, fields)


def linkedin_headers(content_type: str | None = "application/json") -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {getenv('LINKEDIN_ACCESS_TOKEN')}",
        "Linkedin-Version": LINKEDIN_API_VERSION,
        "X-Restli-Protocol-Version": "2.0.0",
    }
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def linkedin_upload_headers(content_type: str | None) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {getenv('LINKEDIN_ACCESS_TOKEN')}",
        "Content-Type": content_type or "application/octet-stream",
    }


def linkedin_post_json(path: str, payload: dict[str, Any]) -> tuple[dict[str, Any], Any]:
    request = Request(
        f"{LINKEDIN_API_BASE_URL}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers=linkedin_headers(),
        method="POST",
    )

    with urlopen(request, timeout=60) as response:
        body = response.read()
        data = json.loads(body.decode("utf-8")) if body else {}
        return data, response.headers


def linkedin_put_file(
    upload_url: str,
    file_path: Path,
    content_type: str | None,
    first_byte: int | None = None,
    last_byte: int | None = None,
) -> str:
    data = file_path.read_bytes()
    if first_byte is not None and last_byte is not None:
        data = data[first_byte : last_byte + 1]

    request = Request(
        upload_url,
        data=data,
        headers=linkedin_upload_headers(content_type),
        method="PUT",
    )

    with urlopen(request, timeout=120) as response:
        response.read()
        return response.headers.get("etag", "").strip('"')


async def post_linkedin_json(path: str, payload: dict[str, Any]) -> tuple[dict[str, Any], Any]:
    return await asyncio.to_thread(linkedin_post_json, path, payload)


async def put_linkedin_file(
    upload_url: str,
    file_path: Path,
    content_type: str | None,
    first_byte: int | None = None,
    last_byte: int | None = None,
) -> str:
    return await asyncio.to_thread(
        linkedin_put_file,
        upload_url,
        file_path,
        content_type,
        first_byte,
        last_byte,
    )


def linkedin_post_payload(post: dict[str, Any], media_id: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "author": getenv("LINKEDIN_AUTHOR_URN"),
        "commentary": post["caption"] or " ",
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }

    if media_id:
        payload["content"] = {
            "media": {
                "id": media_id,
            }
        }

    return payload


def linkedin_video_post_payload(post: dict[str, Any], video_id: str) -> dict[str, Any]:
    payload = linkedin_post_payload(post)
    payload["content"] = {
        "media": {
            "id": video_id,
        }
    }
    return payload


def twitter_percent_encode(value: Any) -> str:
    return quote(str(value), safe="~")


def twitter_oauth_header(
    method: str,
    url: str,
    request_params: dict[str, Any] | None = None,
) -> str:
    oauth_params = {
        "oauth_consumer_key": getenv("TWITTER_API_KEY"),
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": getenv("TWITTER_ACCESS_TOKEN"),
        "oauth_version": "1.0",
    }
    signature_params = {
        **oauth_params,
        **(request_params or {}),
    }
    parameter_string = "&".join(
        f"{twitter_percent_encode(key)}={twitter_percent_encode(value)}"
        for key, value in sorted(signature_params.items())
    )
    signature_base = "&".join(
        [
            method.upper(),
            twitter_percent_encode(url),
            twitter_percent_encode(parameter_string),
        ]
    )
    signing_key = "&".join(
        [
            twitter_percent_encode(getenv("TWITTER_API_SECRET")),
            twitter_percent_encode(getenv("TWITTER_ACCESS_TOKEN_SECRET")),
        ]
    )
    signature = base64.b64encode(
        hmac.new(
            signing_key.encode("utf-8"),
            signature_base.encode("utf-8"),
            hashlib.sha1,
        ).digest()
    ).decode("utf-8")
    oauth_params["oauth_signature"] = signature

    return "OAuth " + ", ".join(
        f'{twitter_percent_encode(key)}="{twitter_percent_encode(value)}"'
        for key, value in sorted(oauth_params.items())
    )


def twitter_post_json(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"{TWITTER_API_BASE_URL}{path}"
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": twitter_oauth_header("POST", url),
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def twitter_upload_image(file_path: Path, content_type: str | None) -> dict[str, Any]:
    url = f"{TWITTER_UPLOAD_BASE_URL}/1.1/media/upload.json"
    boundary = f"shared-posts-{uuid4().hex}"
    body = bytearray()
    filename = file_path.name

    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(
        (
            f'Content-Disposition: form-data; name="media"; filename="{filename}"\r\n'
            f"Content-Type: {content_type or 'application/octet-stream'}\r\n\r\n"
        ).encode("utf-8")
    )
    body.extend(file_path.read_bytes())
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    request = Request(
        url,
        data=bytes(body),
        headers={
            "Authorization": twitter_oauth_header("POST", url),
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )

    with urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


async def post_twitter_json(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    return await asyncio.to_thread(twitter_post_json, path, payload)


async def upload_twitter_image(file_path: Path, content_type: str | None) -> dict[str, Any]:
    return await asyncio.to_thread(twitter_upload_image, file_path, content_type)


def missing_credentials_result(platform: str) -> dict[str, Any]:
    platform_config = PLATFORMS[platform]
    missing_env = missing_required_env(platform)

    return {
        "platform": platform,
        "status": "needs_credentials",
        "message": f"Missing required environment variables: {', '.join(missing_env)}",
    }


def dry_run_result(platform: str, post: dict[str, Any]) -> dict[str, Any]:
    return {
        "platform": platform,
        "status": "dry_run",
        "message": "Ready to publish after API credentials are configured.",
        "payloadPreview": {
            "caption": post["caption"],
            "mediaUrl": media_url_for(post),
        },
    }


def blocked_result(platform: str, post: dict[str, Any]) -> dict[str, Any] | None:
    if SOCIAL_DRY_RUN:
        return dry_run_result(platform, post)

    missing_env = missing_required_env(platform)
    if missing_env:
        return missing_credentials_result(platform)

    return None


async def publish_to_instagram(post: dict[str, Any]) -> dict[str, Any]:
    blocked = blocked_result("instagram", post)
    if blocked:
        return blocked

    media_url = media_url_for(post, "instagram")
    media = post.get("media")
    if not is_public_https_url(media_url):
        return {
            "platform": "instagram",
            "status": "failed",
            "message": "Instagram publishing needs PUBLIC_API_BASE_URL to be a public HTTPS URL, not localhost.",
        }

    try:
        container_payload = {
            "caption": post["caption"],
            "access_token": getenv("INSTAGRAM_ACCESS_TOKEN"),
        }
        if media["mimeType"].startswith("video/"):
            container_payload.update(
                {
                    "media_type": "REELS",
                    "video_url": media_url,
                    "share_to_feed": "true",
                }
            )
        else:
            container_payload["image_url"] = media_url

        container = await post_form(f"/{getenv('INSTAGRAM_ACCOUNT_ID')}/media", container_payload)
        if media["mimeType"].startswith("video/"):
            video_ready = False
            for _ in range(20):
                status = await get_graph(
                    f"/{container['id']}",
                    {
                        "fields": "status_code",
                        "access_token": getenv("INSTAGRAM_ACCESS_TOKEN"),
                    },
                )
                if status.get("status_code") == "FINISHED":
                    video_ready = True
                    break
                if status.get("status_code") == "ERROR":
                    return {
                        "platform": "instagram",
                        "status": "failed",
                        "message": "Instagram could not process this video.",
                    }
                await asyncio.sleep(3)
            if not video_ready:
                return {
                    "platform": "instagram",
                    "status": "failed",
                    "message": "Instagram video is still processing. Try again in a minute.",
                }

        published = await post_form(
            f"/{getenv('INSTAGRAM_ACCOUNT_ID')}/media_publish",
            {
                "creation_id": container["id"],
                "access_token": getenv("INSTAGRAM_ACCESS_TOKEN"),
            },
        )
    except (HTTPError, URLError, KeyError, TimeoutError) as error:
        return {
            "platform": "instagram",
            "status": "failed",
            "message": graph_api_error(error),
        }

    return {
        "platform": "instagram",
        "status": "published",
        "message": "Published to Instagram.",
        "remoteId": published.get("id"),
    }


async def publish_to_facebook(post: dict[str, Any]) -> dict[str, Any]:
    blocked = blocked_result("facebook", post)
    if blocked:
        return blocked

    page_id = getenv("FACEBOOK_PAGE_ID")
    page_token = getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
    media = post.get("media")

    try:
        if not media:
            published = await post_form(
                f"/{page_id}/feed",
                {
                    "message": post["caption"],
                    "access_token": page_token,
                },
            )
        else:
            media_path = media_path_for(post)
            if media_path is None or not media_path.exists():
                return {
                    "platform": "facebook",
                    "status": "failed",
                    "message": "Uploaded media file is missing.",
                }

            if media["mimeType"].startswith("image/"):
                published = await post_multipart(
                    f"/{page_id}/photos",
                    {
                        "message": post["caption"],
                        "access_token": page_token,
                    },
                    "source",
                    media_path,
                    media["mimeType"],
                )
            elif media["mimeType"].startswith("video/"):
                published = await post_multipart(
                    f"/{page_id}/videos",
                    {
                        "description": post["caption"],
                        "access_token": page_token,
                    },
                    "source",
                    media_path,
                    media["mimeType"],
                )
            else:
                return {
                    "platform": "facebook",
                    "status": "failed",
                    "message": "Facebook only supports image and video uploads here.",
                }
    except (HTTPError, URLError, KeyError, TimeoutError) as error:
        return {
            "platform": "facebook",
            "status": "failed",
            "message": graph_api_error(error),
        }

    return {
        "platform": "facebook",
        "status": "published",
        "message": "Published to Facebook.",
        "remoteId": published.get("id") or published.get("post_id"),
    }


async def publish_to_linkedin(post: dict[str, Any]) -> dict[str, Any]:
    blocked = blocked_result("linkedin", post)
    if blocked:
        return blocked

    media = post.get("media")

    try:
        media_id = None
        post_payload = linkedin_post_payload(post)
        if media:
            media_path = media_path_for(post)
            if media_path is None or not media_path.exists():
                return {
                    "platform": "linkedin",
                    "status": "failed",
                    "message": "Uploaded media file is missing.",
                }

            if media["mimeType"].startswith("video/"):
                initialized, _ = await post_linkedin_json(
                    "/videos?action=initializeUpload",
                    {
                        "initializeUploadRequest": {
                            "owner": getenv("LINKEDIN_AUTHOR_URN"),
                            "fileSizeBytes": media_path.stat().st_size,
                            "uploadCaptions": False,
                            "uploadThumbnail": False,
                        }
                    },
                )
                upload = initialized["value"]
                uploaded_part_ids = []
                for instruction in upload["uploadInstructions"]:
                    etag = await put_linkedin_file(
                        instruction["uploadUrl"],
                        media_path,
                        "application/octet-stream",
                        instruction.get("firstByte"),
                        instruction.get("lastByte"),
                    )
                    if etag:
                        uploaded_part_ids.append(etag)

                await post_linkedin_json(
                    "/videos?action=finalizeUpload",
                    {
                        "finalizeUploadRequest": {
                            "video": upload["video"],
                            "uploadToken": upload.get("uploadToken", ""),
                            "uploadedPartIds": uploaded_part_ids,
                        }
                    },
                )
                post_payload = linkedin_video_post_payload(post, upload["video"])
            else:
                initialized, _ = await post_linkedin_json(
                    "/images?action=initializeUpload",
                    {
                        "initializeUploadRequest": {
                            "owner": getenv("LINKEDIN_AUTHOR_URN"),
                        }
                    },
                )
                upload = initialized["value"]
                await put_linkedin_file(upload["uploadUrl"], media_path, media["mimeType"])
                media_id = upload["image"]
                post_payload = linkedin_post_payload(post, media_id)

        _, headers = await post_linkedin_json("/posts", post_payload)
    except (HTTPError, URLError, KeyError, TimeoutError) as error:
        return {
            "platform": "linkedin",
            "status": "failed",
            "message": graph_api_error(error),
        }

    return {
        "platform": "linkedin",
        "status": "published",
        "message": "Published to LinkedIn.",
        "remoteId": headers.get("x-restli-id"),
    }


async def publish_to_twitter(post: dict[str, Any]) -> dict[str, Any]:
    blocked = blocked_result("twitter", post)
    if blocked:
        return blocked

    media = post.get("media")

    try:
        payload: dict[str, Any] = {}
        if post["caption"]:
            payload["text"] = post["caption"]

        if media:
            if not media["mimeType"].startswith("image/"):
                return {
                    "platform": "twitter",
                    "status": "failed",
                    "message": "X/Twitter video publishing is not wired yet. Use an image or text-only post.",
                }

            media_path = media_path_for(post)
            if media_path is None or not media_path.exists():
                return {
                    "platform": "twitter",
                    "status": "failed",
                    "message": "Uploaded media file is missing.",
                }

            uploaded = await upload_twitter_image(media_path, media["mimeType"])
            payload["media"] = {
                "media_ids": [uploaded.get("media_id_string") or str(uploaded["media_id"])],
            }

        published = await post_twitter_json("/2/tweets", payload)
    except (HTTPError, URLError, KeyError, TimeoutError) as error:
        return {
            "platform": "twitter",
            "status": "failed",
            "message": graph_api_error(error),
        }

    return {
        "platform": "twitter",
        "status": "published",
        "message": "Published to X / Twitter.",
        "remoteId": published.get("data", {}).get("id"),
    }


ADAPTERS = {
    "instagram": publish_to_instagram,
    "facebook": publish_to_facebook,
    "linkedin": publish_to_linkedin,
    "twitter": publish_to_twitter,
}
