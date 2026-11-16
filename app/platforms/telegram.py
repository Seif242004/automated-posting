from app.config import env
from app.platforms.base import BasePlatform, Posted, PlatformError, check


class Telegram(BasePlatform):
    """Telegram Bot API - https://core.telegram.org/bots/api#sendmessage"""

    name = "Telegram"

    def is_configured(self) -> bool:
        return bool(env("TELEGRAM_BOT_TOKEN") and env("TELEGRAM_CHANNEL"))

    async def publish(self, client, message, link) -> Posted:
        token, channel = env("TELEGRAM_BOT_TOKEN"), env("TELEGRAM_CHANNEL")
        data = check(
            await client.post(
                f"{env('TELEGRAM_API_BASE', 'https://api.telegram.org').rstrip('/')}/bot{token}/sendMessage",
                json={"chat_id": channel, "text": message},
            ),
            "Telegram",
        )
        if not data.get("ok"):
            raise PlatformError(data.get("description", "Telegram rejected the message"))
        msg_id = data["result"]["message_id"]
        username = data["result"]["chat"].get("username")
        if username:  # public channel -> public link
            return Posted(f"https://t.me/{username}/{msg_id}", public=True)
        return Posted(None, public=False)
