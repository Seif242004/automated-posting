"""Local MOCK of the five platform APIs, for demos without real credentials.

NOT real services: nothing here is posted anywhere. Run:
    uvicorn mock.mock_platforms:app --port 5000
"""
import itertools

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse

app = FastAPI(title="Mock platform APIs (simulation)")
ids = itertools.count(1001)
posts: dict[str, str] = {}
BASE = "http://localhost:5000"


@app.post("/bot{token}/sendMessage")
async def telegram(token: str, req: Request):
    if token != "demo-token":
        raise HTTPException(401, "Unauthorized")
    body = await req.json()
    return {"ok": True, "result": {"message_id": next(ids), "chat": {"username": body["chat_id"].lstrip("@")},
                                   "text": body["text"]}}


@app.post("/discord/webhook")
async def discord(req: Request):
    body = await req.json()
    return {"id": str(next(ids)), "channel_id": "555", "content": body["content"]}


@app.post("/api/v1/statuses")
async def mastodon(req: Request, authorization: str = Header("")):
    if authorization != "Bearer demo-token":
        raise HTTPException(401, "The access token is invalid")
    body = await req.json()
    pid = str(next(ids))
    posts[f"/@demo/{pid}"] = body["status"]
    return {"id": pid, "url": f"{BASE}/@demo/{pid}", "visibility": body["visibility"]}


@app.get("/@demo/{pid}", response_class=HTMLResponse)
async def view_status(pid: str):
    text = posts.get(f"/@demo/{pid}")
    if text is None:
        raise HTTPException(404)
    return f"<p>{text}</p>"


@app.post("/xrpc/com.atproto.server.createSession")
async def bsky_session(req: Request):
    body = await req.json()
    if body["password"] != "demo-pass":
        raise HTTPException(401, "Invalid identifier or password")
    return {"accessJwt": "jwt", "did": "did:plc:demo", "handle": body["identifier"]}


@app.post("/xrpc/com.atproto.repo.createRecord")
async def bsky_record(req: Request):
    body = await req.json()
    return {"uri": f"at://{body['repo']}/app.bsky.feed.post/{next(ids)}", "cid": "x"}


@app.post("/api/articles")
async def devto(req: Request, api_key: str = Header("")):
    if api_key != "demo-key":
        raise HTTPException(401, "unauthorized")
    aid = next(ids)
    return {"id": aid, "url": f"{BASE}/devto/demo/{aid}"}


@app.get("/devto/demo/{pid}", response_class=HTMLResponse)
async def view_article(pid: str):
    return "<p>mock article</p>"
