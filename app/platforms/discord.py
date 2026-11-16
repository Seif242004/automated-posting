from app.config import env
from app.platforms.base import BasePlatform, Posted, check


class Discord(BasePlatform):
    """Discord webhook - https://discord.com/developers/docs/resources/webhook#execute-webhook"""

    name = "Discord"

    def is_configured(self) -> bool:
        return bool(env("DISCORD_WEBHOOK_URL"))

    async def publish(self, client, message, link) -> Posted:
        data = check(
            await client.post(
                env("DISCORD_WEBHOOK_URL"),
                params={"wait": "true"},  # return the created message
                json={"content": message},
            ),
            "Discord",
        )
        guild = env("DISCORD_GUILD_ID") or data.get("guild_id")
        url = (
            f"https://discord.com/channels/{guild}/{data['channel_id']}/{data['id']}"
            if guild
            else None
        )
        # Discord message links need server membership, so they are never anonymously viewable.
        return Posted(url, public=False)
