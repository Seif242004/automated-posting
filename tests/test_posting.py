import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.platforms.base import BasePlatform, PlatformError, Posted
from app.platforms.bluesky import Bluesky
from app.platforms.mastodon import Mastodon
from app.services import posting_service

client = TestClient(app)
GOOD = "Check out our platform https://example.com"


class OK(BasePlatform):
    name = "OK"
    def is_configured(self): return True
    async def publish(self, c, m, l): return Posted("https://ok.test/1", public=True)


class Boom(BasePlatform):
    name = "Boom"
    def is_configured(self): return True
    async def publish(self, c, m, l): raise PlatformError("Authentication failed")


class Crash(BasePlatform):
    name = "Crash"
    def is_configured(self): return True
    async def publish(self, c, m, l): raise RuntimeError("kaboom")


class Unconfigured(OK):
    name = "Unconfigured"
    def is_configured(self): return False


# ---------- validation ----------
@pytest.mark.parametrize("msg", [
    "x" * 201,                                   # too long
    "",                                          # empty
    "No link here",                              # no link
    "Two https://a.com and https://b.com",       # two links
    "Bad link http://nodot",                     # invalid URL
    "ftp://example.com is not http",             # wrong scheme -> no match
])
def test_invalid_messages_rejected(msg):
    r = client.post("/posting", json={"message": msg})
    assert r.status_code == 422
    assert r.json()["success"] is False


def test_missing_body_field():
    assert client.post("/posting", json={}).status_code == 422


def test_exactly_200_chars_ok(monkeypatch):
    monkeypatch.setattr(posting_service, "default_platforms", lambda: [OK()])
    link = "https://example.com"
    msg = "a" * (200 - len(link) - 1) + " " + link
    assert len(msg) == 200
    assert client.post("/posting", json={"message": msg}).status_code == 200


# ---------- fan-out & isolation ----------
def test_failures_do_not_block_others(monkeypatch):
    monkeypatch.setattr(posting_service, "default_platforms",
                        lambda: [Boom(), OK(), Crash(), Unconfigured()])
    r = client.post("/posting", json={"message": GOOD})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    by = {x["platform"]: x for x in body["results"]}
    assert by["OK"]["status"] == "success" and by["OK"]["posted_url"] == "https://ok.test/1"
    assert by["OK"]["public_access"] is True and by["OK"]["date"] and by["OK"]["time"]
    assert by["Boom"]["status"] == "failed" and by["Boom"]["error"] == "Authentication failed"
    assert by["Boom"]["posted_url"] is None and by["Boom"]["date"] is None
    assert "kaboom" in by["Crash"]["error"]
    assert "Missing credentials" in by["Unconfigured"]["error"]


def test_all_failed_marks_success_false(monkeypatch):
    monkeypatch.setattr(posting_service, "default_platforms", lambda: [Boom()])
    assert client.post("/posting", json={"message": GOOD}).json()["success"] is False


# ---------- real adapters against mocked HTTP ----------
@pytest.mark.anyio
async def test_mastodon_adapter(monkeypatch):
    monkeypatch.setenv("MASTODON_INSTANCE", "https://masto.test")
    monkeypatch.setenv("MASTODON_ACCESS_TOKEN", "t")

    def handler(req: httpx.Request):
        if req.method == "POST":
            assert req.headers["authorization"] == "Bearer t"
            return httpx.Response(200, json={"url": "https://masto.test/@me/1"})
        return httpx.Response(200, text="ok")  # anonymous GET -> public

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
        res = await Mastodon().post(GOOD, "https://example.com", c)
    assert res.status == "success" and res.public_access is True


@pytest.mark.anyio
async def test_bluesky_auth_failure(monkeypatch):
    monkeypatch.setenv("BLUESKY_HANDLE", "me.bsky.social")
    monkeypatch.setenv("BLUESKY_APP_PASSWORD", "bad")
    transport = httpx.MockTransport(lambda r: httpx.Response(401, json={"error": "AuthenticationRequired"}))
    async with httpx.AsyncClient(transport=transport) as c:
        res = await Bluesky().post(GOOD, "https://example.com", c)
    assert res.status == "failed" and "Authentication failed" in res.error


@pytest.fixture
def anyio_backend():
    return "asyncio"
