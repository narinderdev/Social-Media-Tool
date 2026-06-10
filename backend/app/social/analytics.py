import asyncio
import json
from datetime import UTC, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from app.social.adapters import (
    GRAPH_API_BASE_URL,
    LINKEDIN_API_BASE_URL,
    TWITTER_API_BASE_URL,
    api_error_message,
    credential,
    graph_api_error,
    linkedin_headers,
    twitter_oauth_header,
)

METRIC_REFRESH_SECONDS = 3 * 60 * 60


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def empty_values() -> dict[str, int | None]:
    return {
        "impressions": None,
        "views": None,
        "reach": None,
        "engagements": None,
        "likes": None,
        "comments": None,
        "shares": None,
        "clicks": None,
        "saves": None,
    }


def platform_metric(
    platform: str,
    status: str,
    message: str,
    remote_id: str | None = None,
    values: dict[str, int | None] | None = None,
    raw: dict[str, Any] | None = None,
    unavailable_metrics: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "platform": platform,
        "status": status,
        "message": message,
        "remoteId": remote_id,
        "updatedAt": now_iso(),
        "values": {**empty_values(), **(values or {})},
        "raw": raw or {},
        "unavailableMetrics": unavailable_metrics or [],
    }


def int_value(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def graph_get_json(path: str, fields: dict[str, Any]) -> dict[str, Any]:
    query = urlencode({key: value for key, value in fields.items() if value is not None})
    request = Request(f"{GRAPH_API_BASE_URL}{path}?{query}", method="GET")

    with urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


async def get_graph_json(path: str, fields: dict[str, Any]) -> dict[str, Any]:
    return await asyncio.to_thread(graph_get_json, path, fields)


def linkedin_get_json(post: dict[str, Any], path: str) -> dict[str, Any]:
    request = Request(
        f"{LINKEDIN_API_BASE_URL}{path}",
        headers=linkedin_headers(post, content_type=None),
        method="GET",
    )

    with urlopen(request, timeout=60) as response:
        body = response.read()
        return json.loads(body.decode("utf-8")) if body else {}


async def get_linkedin_json(post: dict[str, Any], path: str) -> dict[str, Any]:
    return await asyncio.to_thread(linkedin_get_json, post, path)


def twitter_get_json(post: dict[str, Any], path: str, params: dict[str, Any]) -> dict[str, Any]:
    query = urlencode({key: value for key, value in params.items() if value is not None})
    base_url = f"{TWITTER_API_BASE_URL}{path}"
    url = f"{base_url}?{query}"
    request = Request(
        url,
        headers={"Authorization": twitter_oauth_header("GET", base_url, post, params)},
        method="GET",
    )

    with urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


async def get_twitter_json(
    post: dict[str, Any],
    path: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    return await asyncio.to_thread(twitter_get_json, post, path, params)


def numeric_total(value: Any) -> int | None:
    numeric_value = int_value(value)
    if numeric_value is not None:
        return numeric_value

    if isinstance(value, dict):
        values = [int_value(item) for item in value.values()]
        numeric_values = [item for item in values if item is not None]
        if numeric_values:
            return sum(numeric_values)

    return None


def insight_value(response: dict[str, Any], metric_name: str) -> int | None:
    for item in response.get("data", []):
        if item.get("name") != metric_name:
            continue
        values = item.get("values") or []
        if not values:
            return None
        value = values[0].get("value")
        return numeric_total(value)
    return None


async def fetch_graph_insight(
    remote_id: str,
    token: str | None,
    metric_name: str,
) -> tuple[int | None, dict[str, Any] | None, str | None]:
    try:
        response = await get_graph_json(
            f"/{remote_id}/insights",
            {"metric": metric_name, "access_token": token},
        )
        return insight_value(response, metric_name), response, None
    except (HTTPError, URLError, KeyError, TimeoutError) as error:
        return None, None, graph_api_error(error)


async def fetch_graph_field_counts(
    remote_id: str,
    token: str | None,
    fields: str,
) -> dict[str, Any]:
    return await get_graph_json(f"/{remote_id}", {"fields": fields, "access_token": token})


async def fetch_graph_edge_summary(
    remote_id: str,
    token: str | None,
    edge: str,
) -> tuple[int | None, dict[str, Any] | None, str | None]:
    try:
        response = await get_graph_json(
            f"/{remote_id}/{edge}",
            {"summary": "true", "limit": 0, "access_token": token},
        )
        return count_from_summary(response), response, None
    except (HTTPError, URLError, KeyError, TimeoutError) as error:
        return None, None, graph_api_error(error)


async def resolve_facebook_post_id(
    remote_id: str,
    token: str | None,
) -> tuple[str, dict[str, Any] | None, str | None]:
    if "_" in remote_id:
        return remote_id, None, None

    try:
        response = await fetch_graph_field_counts(remote_id, token, "post_id")
        post_id = response.get("post_id")
        if post_id:
            return post_id, response, None
        return remote_id, response, "No linked Facebook feed post ID returned."
    except (HTTPError, URLError, KeyError, TimeoutError) as error:
        return remote_id, None, graph_api_error(error)


def count_from_summary(container: Any) -> int | None:
    if not isinstance(container, dict):
        return None
    summary = container.get("summary")
    if isinstance(summary, dict):
        return int_value(summary.get("total_count"))
    return None


def all_metric_keys() -> list[str]:
    return list(empty_values().keys())


def error_means_unavailable_metric(error: str | None) -> bool:
    if not error:
        return False

    value = error.lower()
    return any(
        pattern in value
        for pattern in (
            "permission",
            "permissions",
            "not enough",
            "does not have access",
            "valid insights metric",
            "cannot be accessed",
            "tried accessing nonexisting field",
            "unsupported",
        )
    )


def linkedin_metric_error_message(message: str) -> str:
    if "partnerapisocialmetadata" in message.lower():
        return (
            "LinkedIn personal posting is configured, but this token only has publish access. "
            "LinkedIn stats for personal posts require restricted read/social metadata access."
        )

    return message


def facebook_metric_message(status: str, errors: list[str]) -> str:
    if status == "available":
        return "Facebook post insights refreshed."
    if status == "partial":
        return "Facebook engagement counts refreshed from post edges."

    combined_errors = " ".join(errors).lower()
    if "unsupported get request" in combined_errors or "does not exist" in combined_errors:
        return (
            "Facebook stats unavailable: Meta could not load this post ID. "
            "It may be missing, deleted, not published to the page feed, or inaccessible to this page token."
        )
    if any(error_means_unavailable_metric(error) for error in errors):
        return (
            "Facebook stats unavailable: Meta did not return these metrics with the current "
            "post ID and page permissions."
        )

    return "No Facebook metrics returned."


async def fetch_instagram_metrics(post: dict[str, Any], remote_id: str) -> dict[str, Any]:
    token = credential(post, "INSTAGRAM_ACCESS_TOKEN")
    metric_map = {
        "views": ("views", "views"),
        "reach": ("reach", "reach"),
        "likes": ("likes", "likes"),
        "comments": ("comments", "comments"),
        "shares": ("shares", "shares"),
        "saves": ("saved", "saves"),
        "engagements": ("total_interactions", "engagements"),
    }
    values: dict[str, int | None] = {}
    raw: dict[str, Any] = {}
    errors: list[str] = []

    for graph_metric, normalized_metric in metric_map.values():
        value, response, error = await fetch_graph_insight(remote_id, token, graph_metric)
        if value is not None:
            values[normalized_metric] = value
        if response:
            raw[graph_metric] = response
        if error:
            errors.append(f"{graph_metric}: {error}")

    try:
        counts = await fetch_graph_field_counts(
            remote_id,
            token,
            "like_count,comments_count",
        )
        raw["counts"] = counts
        like_count = int_value(counts.get("like_count"))
        comment_count = int_value(counts.get("comments_count"))
        if like_count is not None:
            values["likes"] = max(values.get("likes") or 0, like_count)
        if comment_count is not None:
            values["comments"] = max(values.get("comments") or 0, comment_count)
    except (HTTPError, URLError, KeyError, TimeoutError) as error:
        errors.append(f"counts: {graph_api_error(error)}")

    engagement_parts = [
        values.get("likes"),
        values.get("comments"),
        values.get("shares"),
        values.get("saves"),
    ]
    if values.get("engagements") is None and any(value is not None for value in engagement_parts):
        values["engagements"] = sum(value or 0 for value in engagement_parts)

    status = "available" if any(value is not None for value in values.values()) else "unavailable"
    return platform_metric(
        "instagram",
        status,
        (
            "Instagram insights refreshed."
            if status == "available"
            else "; ".join(errors) or "No Instagram insights returned."
        ),
        remote_id,
        values,
        raw,
    )


async def fetch_facebook_metrics(post: dict[str, Any], remote_id: str) -> dict[str, Any]:
    token = credential(post, "FACEBOOK_PAGE_ACCESS_TOKEN")
    post_id, resolved_raw, resolve_error = await resolve_facebook_post_id(remote_id, token)
    values: dict[str, int | None] = {}
    raw: dict[str, Any] = {}
    errors: list[str] = []
    unavailable_metrics: set[str] = set()

    if resolved_raw:
        raw["resolved_post"] = resolved_raw
    if resolve_error:
        errors.append(f"post_id: {resolve_error}")

    for graph_metric, normalized_metric in {
        "post_media_view": "impressions",
        "post_total_media_view_unique": "reach",
        "post_activity_by_action_type": "engagements",
        "post_clicks": "clicks",
        "post_reactions_by_type_total": "likes",
    }.items():
        value, response, error = await fetch_graph_insight(post_id, token, graph_metric)
        if value is not None:
            values[normalized_metric] = value
            if graph_metric == "post_media_view":
                values["views"] = value
        if response:
            raw[graph_metric] = response
        if error:
            errors.append(f"{graph_metric}: {error}")
            if error_means_unavailable_metric(error):
                unavailable_metrics.add(normalized_metric)
                if graph_metric == "post_media_view":
                    unavailable_metrics.add("views")

    for edge, normalized_metric in {
        "reactions": "likes",
        "comments": "comments",
        "sharedposts": "shares",
    }.items():
        value, response, error = await fetch_graph_edge_summary(post_id, token, edge)
        if value is not None:
            current_value = values.get(normalized_metric)
            values[normalized_metric] = max(current_value or 0, value)
        if response:
            raw[edge] = response
        if error:
            errors.append(f"{edge}: {error}")
            if error_means_unavailable_metric(error):
                unavailable_metrics.add(normalized_metric)

    engagement_parts = [
        values.get("likes"),
        values.get("comments"),
        values.get("shares"),
        values.get("clicks"),
    ]
    if values.get("engagements") is None and any(value is not None for value in engagement_parts):
        values["engagements"] = sum(value or 0 for value in engagement_parts)

    has_insight_values = any(
        values.get(metric) is not None
        for metric in ("impressions", "reach", "engagements", "clicks", "views")
    )
    status = "available" if has_insight_values else "partial" if any(value is not None for value in values.values()) else "unavailable"
    return platform_metric(
        "facebook",
        status,
        facebook_metric_message(status, errors),
        post_id,
        values,
        raw,
        sorted(unavailable_metrics),
    )


def linkedin_reaction_count(reaction_summaries: Any) -> int | None:
    if not isinstance(reaction_summaries, dict):
        return None
    total = 0
    found = False
    for summary in reaction_summaries.values():
        value = int_value(summary.get("count") if isinstance(summary, dict) else None)
        if value is not None:
            total += value
            found = True
    return total if found else None


async def fetch_linkedin_metrics(post: dict[str, Any], remote_id: str) -> dict[str, Any]:
    try:
        response = await get_linkedin_json(post, f"/socialMetadata/{quote(remote_id, safe='')}")
    except HTTPError as error:
        try:
            body = json.loads(error.read().decode("utf-8"))
            message = api_error_message(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            message = str(error.reason)
        return platform_metric(
            "linkedin",
            "unavailable",
            linkedin_metric_error_message(message),
            remote_id,
            unavailable_metrics=all_metric_keys(),
        )
    except (URLError, KeyError, TimeoutError) as error:
        return platform_metric(
            "linkedin",
            "unavailable",
            str(error),
            remote_id,
            unavailable_metrics=all_metric_keys(),
        )

    comment_summary = response.get("commentSummary") or {}
    values = {
        "likes": linkedin_reaction_count(response.get("reactionSummaries")),
        "comments": int_value(comment_summary.get("count")),
    }
    return platform_metric(
        "linkedin",
        "partial",
        (
            "LinkedIn reactions and comments refreshed. Impressions/views require restricted "
            "LinkedIn analytics access."
        ),
        remote_id,
        values,
        response,
        ["clicks", "engagements", "impressions", "reach", "saves", "shares", "views"],
    )


async def fetch_twitter_metrics(post: dict[str, Any], remote_id: str) -> dict[str, Any]:
    try:
        response = await get_twitter_json(
            post,
            f"/2/tweets/{remote_id}",
            {
                "tweet.fields": "attachments,public_metrics,non_public_metrics,organic_metrics",
                "expansions": "attachments.media_keys",
                "media.fields": "public_metrics,non_public_metrics",
            },
        )
    except HTTPError as error:
        try:
            body = json.loads(error.read().decode("utf-8"))
            message = api_error_message(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            message = str(error.reason)
        return platform_metric("twitter", "unavailable", message, remote_id)
    except (URLError, KeyError, TimeoutError) as error:
        return platform_metric("twitter", "unavailable", str(error), remote_id)

    data = response.get("data") or {}
    public_metrics = data.get("public_metrics") or {}
    non_public_metrics = data.get("non_public_metrics") or {}
    organic_metrics = data.get("organic_metrics") or {}
    media_items = response.get("includes", {}).get("media", [])
    video_views = next(
        (
            int_value((media.get("public_metrics") or {}).get("view_count"))
            for media in media_items
            if int_value((media.get("public_metrics") or {}).get("view_count")) is not None
        ),
        None,
    )
    values = {
        "impressions": int_value(
            public_metrics.get("impression_count")
            or organic_metrics.get("impression_count")
            or non_public_metrics.get("impression_count")
        ),
        "views": video_views,
        "engagements": int_value(non_public_metrics.get("engagements")),
        "likes": int_value(public_metrics.get("like_count") or organic_metrics.get("like_count")),
        "comments": int_value(
            public_metrics.get("reply_count") or organic_metrics.get("reply_count")
        ),
        "shares": int_value(
            public_metrics.get("retweet_count") or organic_metrics.get("retweet_count")
        ),
        "clicks": int_value(
            non_public_metrics.get("url_link_clicks")
            or organic_metrics.get("url_link_clicks")
            or non_public_metrics.get("user_profile_clicks")
            or organic_metrics.get("user_profile_clicks")
        ),
        "saves": int_value(public_metrics.get("bookmark_count")),
    }
    return platform_metric(
        "twitter",
        "available",
        "X / Twitter metrics refreshed.",
        remote_id,
        values,
        response,
    )


FETCHERS = {
    "instagram": fetch_instagram_metrics,
    "facebook": fetch_facebook_metrics,
    "linkedin": fetch_linkedin_metrics,
    "twitter": fetch_twitter_metrics,
}


def published_result_for(post: dict[str, Any], platform: str) -> dict[str, Any] | None:
    for result in post.get("results", []):
        if result.get("platform") == platform and result.get("remoteId"):
            return result
    return None


async def fetch_post_metrics(
    post: dict[str, Any],
    selected_platforms: list[str] | None = None,
) -> dict[str, Any]:
    platform_metrics: dict[str, Any] = {}
    platforms = selected_platforms or post.get("platforms", [])

    for platform in platforms:
        if platform not in post.get("platforms", []):
            continue

        result = published_result_for(post, platform)
        if not result:
            platform_metrics[platform] = platform_metric(
                platform,
                "unavailable",
                "No remote post ID saved for this platform.",
            )
            continue

        fetcher = FETCHERS.get(platform)
        if fetcher is None:
            platform_metrics[platform] = platform_metric(
                platform,
                "unsupported",
                "No analytics adapter exists for this platform.",
                result.get("remoteId"),
            )
            continue

        try:
            platform_metrics[platform] = await fetcher(post, result["remoteId"])
        except Exception as error:
            platform_metrics[platform] = platform_metric(
                platform,
                "unavailable",
                str(error) or "Unknown analytics error.",
                result.get("remoteId"),
            )

    return {
        "updatedAt": now_iso(),
        "platforms": platform_metrics,
    }


def should_refresh_metrics(post: dict[str, Any], refresh_seconds: int = METRIC_REFRESH_SECONDS) -> bool:
    if post.get("status") not in {"published", "partial_failed"}:
        return False
    if not any(result.get("remoteId") for result in post.get("results", [])):
        return False

    updated_at = post.get("metrics", {}).get("updatedAt")
    if not updated_at:
        return True

    try:
        last_refresh = datetime.fromisoformat(updated_at)
    except ValueError:
        return True

    if last_refresh.tzinfo is None:
        last_refresh = last_refresh.replace(tzinfo=UTC)

    return (datetime.now(UTC) - last_refresh).total_seconds() >= refresh_seconds
