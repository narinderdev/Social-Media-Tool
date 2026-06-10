import asyncio
from datetime import UTC, datetime

from app.social.analytics import METRIC_REFRESH_SECONDS, fetch_post_metrics, should_refresh_metrics
from app.social.publisher import publish_post
from app.storage import read_due_scheduled_posts, read_posts, save_post_stats, update_post

_scheduler_task: asyncio.Task | None = None
_analytics_task: asyncio.Task | None = None
_publish_lock = asyncio.Lock()
_analytics_lock = asyncio.Lock()


def start_scheduler() -> None:
    global _analytics_task, _scheduler_task
    if _scheduler_task is None or _scheduler_task.done():
        _scheduler_task = asyncio.create_task(schedule_loop())
    if _analytics_task is None or _analytics_task.done():
        _analytics_task = asyncio.create_task(analytics_loop())


async def stop_scheduler() -> None:
    tasks = [task for task in (_scheduler_task, _analytics_task) if task is not None]
    if not tasks:
        return

    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)


async def schedule_loop() -> None:
    while True:
        await publish_due_posts()
        await asyncio.sleep(30)


async def analytics_loop() -> None:
    await asyncio.sleep(60)
    while True:
        await refresh_due_metrics()
        await asyncio.sleep(METRIC_REFRESH_SECONDS)


async def publish_due_posts() -> None:
    async with _publish_lock:
        for post in read_due_scheduled_posts():
            if post.get("status") != "scheduled":
                continue

            publishing_post = {
                **post,
                "status": "publishing",
                "results": [
                    {
                        **result,
                        "status": "publishing",
                        "message": "Publishing scheduled post now.",
                    }
                    for result in post.get("results", [])
                ],
            }
            update_post(publishing_post)

            results = await publish_post(publishing_post)
            failed_results = [result for result in results if result["status"] != "published"]
            published_results = [result for result in results if result["status"] == "published"]
            update_post(
                {
                    **publishing_post,
                    "status": (
                        "partial_failed"
                        if failed_results and published_results
                        else "failed"
                        if failed_results
                        else "published"
                    ),
                    "publishedAt": datetime.now(UTC).isoformat(),
                    "results": results,
                }
            )


async def refresh_due_metrics() -> None:
    async with _analytics_lock:
        for post in read_posts():
            if not should_refresh_metrics(post):
                continue

            metrics = await fetch_post_metrics(post)
            save_post_stats(post, metrics)
