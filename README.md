# Automated Multi-Platform Posting (FastAPI)

`POST /posting` takes a short message with one CTA link and publishes it to five platforms concurrently through their official APIs. A failure on one platform never stops the others.

## Platforms

| Platform | API | Auth | Posted URL |
|---|---|---|---|
| Telegram | [Bot API `sendMessage`](https://core.telegram.org/bots/api#sendmessage) | Bot token + public channel | `t.me/<channel>/<id>` |
| Discord | [Webhook execute](https://discord.com/developers/docs/resources/webhook#execute-webhook) | Webhook URL | `discord.com/channels/...` (members only, so `public_access: false`) |
| Mastodon | [`POST /api/v1/statuses`](https://docs.joinmastodon.org/methods/statuses/#create) | Access token | status URL |
| Bluesky | [AT Protocol `createRecord`](https://docs.bsky.app/docs/tutorials/creating-a-post) | Handle + app password | `bsky.app/profile/<handle>/post/<id>` |
| Dev.to | [Forem API `createArticle`](https://developers.forem.com/api/v1#tag/articles/operation/createArticle) | API key | article URL |

`public_access` is verified with an anonymous GET of the posted URL (Mastodon, Dev.to). For Telegram and Bluesky it is derived from the channel or post being public. It is always `false` for Discord.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env              # then fill in credentials (never commit .env)
uvicorn app.main:app --host 0.0.0.0 --port 4000
```

Docs: http://localhost:4000/docs. Platforms without credentials simply report `failed` with "Missing credentials".

Tests: `pytest` (HTTP is mocked, so no credentials are needed).

## Validation rules

- Message is required and at most 200 characters.
- Exactly one link (`http(s)://...` or `www....`) with a valid host. Zero or several links are rejected.
- Invalid input returns **422** with `{"success": false, "errors": [{"field", "message"}]}`.

## Sample

```bash
curl -X POST http://localhost:4000/posting -H "Content-Type: application/json" \
  -d '{"message":"Check out our latest business platform and grow your online visibility. https://example.com"}'
```

Response (a run with no credentials configured, captured from the real server):

```json
{
  "success": false,
  "results": [
    {"platform": "Telegram", "status": "failed", "posted_url": null, "public_access": false,
     "date": null, "time": null, "error": "Missing credentials (see .env.example)"}
  ]
}
```

With credentials, a successful entry looks like:

```json
{"platform": "Mastodon", "status": "success", "posted_url": "https://mastodon.social/@me/1123",
 "public_access": true, "date": "2026-11-16", "time": "10:30:00", "error": null}
```

`success` is `true` when at least one platform succeeded.

Validation errors:

```json
{"success": false, "errors": [{"field": "message", "message": "Message must contain exactly one CTA link (found 2)"}]}
{"success": false, "errors": [{"field": "message", "message": "Message must not exceed 200 characters (got 229)"}]}
```

Server log from the run: the logs under `docs/`.

## Demo without real credentials (simulation)

No real accounts were used for the included output. `mock/mock_platforms.py` is a **local mock** that imitates the five platform APIs, and the adapters are pointed at it through optional base-URL variables (`TELEGRAM_API_BASE`, `BLUESKY_PDS`, `DEVTO_API_BASE`, plus the existing `MASTODON_INSTANCE` and `DISCORD_WEBHOOK_URL`). Nothing is posted anywhere. This shows the pipeline, validation, concurrency and error isolation, but it does **not** prove the adapters work against the real services.

```bash
PY=.venv/Scripts/python bash run_demo.sh      # starts mock (port 5000) + app (port 4000), sends one request
```

Mastodon is given a deliberately wrong token, so the output shows 4 successes and 1 isolated failure:
[docs/demo-output.json](docs/demo-output.json), with logs in [docs/demo-app-log.txt](docs/demo-app-log.txt) and [docs/mock-server-log.txt](docs/mock-server-log.txt).

To use real services, fill in `.env` and leave the `*_BASE` variables unset.

## Structure

```
app/main.py                      FastAPI app, /posting route, 422 handler
app/schemas.py                   Pydantic models and message validation
app/config.py                    env-based settings
app/platforms/base.py            BasePlatform: error isolation, public check
app/platforms/<platform>.py      one adapter per platform
app/services/posting_service.py  concurrent fan-out (asyncio.gather)
tests/test_posting.py
```

To add a platform, subclass `BasePlatform` (`is_configured`, `publish`) and register it in `default_platforms()`.
