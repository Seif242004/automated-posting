from app.config import env
from app.platforms.base import BasePlatform, Posted, check


class Mastodon(BasePlatform):
    """Mastodon REST API - https://docs.joinmastodon.org/methods/statuses/#create"""

    name = "Mastodon"

    def is_configured(self) -> bool:
        return bool(env("MASTODON_INSTANCE") and env("MASTODON_ACCESS_TOKEN"))

    async def publish(self, client, message, link) -> Posted:
        base = env("MASTODON_INSTANCE").rstrip("/")
        data = check(
            await client.post(
                f"{base}/api/v1/statuses",
                headers={"Authorization": f"Bearer {env('MASTODON_ACCESS_TOKEN')}"},
                json={"status": message, "visibility": "public"},
            ),
            "Mastodon",
        )
        return Posted(data.get("url"))  # verified with an anonymous GET
