from datetime import datetime

from app.config import env
from app.platforms.base import BasePlatform, Posted, check


class DevTo(BasePlatform):
    """DEV (Forem) API v1 - https://developers.forem.com/api/v1#tag/articles/operation/createArticle"""

    name = "Dev.to"

    def is_configured(self) -> bool:
        return bool(env("DEVTO_API_KEY"))

    async def publish(self, client, message, link) -> Posted:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        article = {
            "title": f"Update {stamp}",
            "body_markdown": message,
            "published": True,
        }
        data = check(
            await client.post(
                f"{env('DEVTO_API_BASE', 'https://dev.to').rstrip('/')}/api/articles",
                headers={"api-key": env("DEVTO_API_KEY"), "Accept": "application/vnd.forem.api-v1+json"},
                json={"article": article},
            ),
            "Dev.to",
        )
        return Posted(data.get("url"))  # verified with an anonymous GET
