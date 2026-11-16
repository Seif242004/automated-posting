from datetime import datetime, timezone

from app.config import env
from app.platforms.base import BasePlatform, Posted, check



class Bluesky(BasePlatform):
    """Bluesky AT Protocol - https://docs.bsky.app/docs/tutorials/creating-a-post"""

    name = "Bluesky"

    def is_configured(self) -> bool:
        return bool(env("BLUESKY_HANDLE") and env("BLUESKY_APP_PASSWORD"))

    async def publish(self, client, message, link) -> Posted:
        PDS = env("BLUESKY_PDS", "https://bsky.social").rstrip("/") + "/xrpc"
        session = check(
            await client.post(
                f"{PDS}/com.atproto.server.createSession",
                json={"identifier": env("BLUESKY_HANDLE"), "password": env("BLUESKY_APP_PASSWORD")},
            ),
            "Bluesky login",
        )
        record = {
            "$type": "app.bsky.feed.post",
            "text": message,
            "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        # Make the link clickable: facets use UTF-8 *byte* offsets.
        raw = message.encode("utf-8")
        start = raw.find(link.encode("utf-8"))
        if start != -1:
            record["facets"] = [{
                "index": {"byteStart": start, "byteEnd": start + len(link.encode("utf-8"))},
                "features": [{"$type": "app.bsky.richtext.facet#link", "uri": link}],
            }]
        data = check(
            await client.post(
                f"{PDS}/com.atproto.repo.createRecord",
                headers={"Authorization": f"Bearer {session['accessJwt']}"},
                json={"repo": session["did"], "collection": "app.bsky.feed.post", "record": record},
            ),
            "Bluesky post",
        )
        rkey = data["uri"].rsplit("/", 1)[-1]
        # Bluesky posts are public by default; the web page is a JS app so skip the GET check.
        return Posted(f"https://bsky.app/profile/{session['handle']}/post/{rkey}", public=True)
