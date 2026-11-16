#!/usr/bin/env bash
# Runs the whole pipeline against the local MOCK APIs (no real credentials, nothing posted).
# Mastodon is given a deliberately wrong token to show failure isolation.
set -e
PY=${PY:-python}
$PY -m uvicorn mock.mock_platforms:app --port 5000 > docs/mock-server-log.txt 2>&1 & MOCK=$!
export TELEGRAM_BOT_TOKEN=demo-token TELEGRAM_CHANNEL=@demo_channel TELEGRAM_API_BASE=http://localhost:5000
export DISCORD_WEBHOOK_URL=http://localhost:5000/discord/webhook DISCORD_GUILD_ID=999
export MASTODON_INSTANCE=http://localhost:5000 MASTODON_ACCESS_TOKEN=WRONG-token
export BLUESKY_HANDLE=demo.bsky.social BLUESKY_APP_PASSWORD=demo-pass BLUESKY_PDS=http://localhost:5000
export DEVTO_API_KEY=demo-key DEVTO_API_BASE=http://localhost:5000
$PY -m uvicorn app.main:app --port 4000 > docs/demo-app-log.txt 2>&1 & APP=$!
trap 'kill $MOCK $APP 2>/dev/null' EXIT
sleep 4
curl -s -X POST localhost:4000/posting -H "Content-Type: application/json" \
  -d '{"message":"Check out our latest business platform and grow your online visibility. https://example.com"}' \
  | $PY -m json.tool > docs/demo-output.json
cat docs/demo-output.json
