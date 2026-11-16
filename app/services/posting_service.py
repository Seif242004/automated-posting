import asyncio

import httpx

from app.config import REQUEST_TIMEOUT
from app.platforms.base import BasePlatform
from app.platforms.bluesky import Bluesky
from app.platforms.devto import DevTo
from app.platforms.discord import Discord
from app.platforms.mastodon import Mastodon
from app.platforms.telegram import Telegram
from app.schemas import PlatformResult, PostingResponse


def default_platforms() -> list[BasePlatform]:
    return [Telegram(), Discord(), Mastodon(), Bluesky(), DevTo()]


async def publish_everywhere(
    message: str, link: str, platforms: list[BasePlatform] | None = None
) -> PostingResponse:
    """Post to all platforms concurrently; each is isolated from the others' failures."""
    platforms = platforms if platforms is not None else default_platforms()
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        results: list[PlatformResult] = await asyncio.gather(
            *(p.post(message, link, client) for p in platforms)
        )
    return PostingResponse(success=any(r.status == "success" for r in results), results=list(results))
