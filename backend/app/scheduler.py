import asyncio
from datetime import UTC, datetime

from app.social.publisher import publish_post
from app.storage import read_due_scheduled_posts, update_post

_scheduler_task: asyncio.Task | None = None
_publish_lock = asyncio.Lock()


def start_scheduler() -> None:
    global _scheduler_task
    if _scheduler_task is None or _scheduler_task.done():
        _scheduler_task = asyncio.create_task(schedule_loop())


async def stop_scheduler() -> None:
    if _scheduler_task is None:
        return

    _scheduler_task.cancel()
    try:
        await _scheduler_task
    except asyncio.CancelledError:
        pass


async def schedule_loop() -> None:
    while True:
        await publish_due_posts()
        await asyncio.sleep(30)


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
