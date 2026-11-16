from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

import httpx

from app.config import REQUEST_TIMEOUT
from app.schemas import PlatformResult


class PlatformError(Exception):
    """Expected, user-presentable failure (bad credentials, API error...)."""


@dataclass
class Posted:
    url: str | None
    public: bool | None = None  # None -> verify by fetching the URL


class BasePlatform(ABC):
    name: str = "base"

    @abstractmethod
    def is_configured(self) -> bool: ...

    @abstractmethod
    async def publish(self, client: httpx.AsyncClient, message: str, link: str) -> Posted: ...

    async def _is_public(self, client: httpx.AsyncClient, url: str | None) -> bool:
        """Anonymous GET (no credentials) of the posted URL."""
        if not url:
            return False
        try:
            r = await client.get(url, follow_redirects=True, timeout=REQUEST_TIMEOUT)
            return r.status_code == 200
        except httpx.HTTPError:
            return False

    async def post(self, message: str, link: str, client: httpx.AsyncClient | None = None) -> PlatformResult:
        """Never raises: every outcome is converted into a PlatformResult."""
        if not self.is_configured():
            return self._fail("Missing credentials (see .env.example)")
        own = client is None
        client = client or httpx.AsyncClient(timeout=REQUEST_TIMEOUT)
        try:
            posted = await self.publish(client, message, link)
            public = posted.public if posted.public is not None else await self._is_public(client, posted.url)
            now = datetime.now()
            return PlatformResult(
                platform=self.name,
                status="success",
                posted_url=posted.url,
                public_access=public,
                date=now.strftime("%Y-%m-%d"),
                time=now.strftime("%H:%M:%S"),
            )
        except PlatformError as e:
            return self._fail(str(e))
        except httpx.TimeoutException:
            return self._fail("Request timed out")
        except httpx.HTTPError as e:
            return self._fail(f"Network error: {e}")
        except Exception as e:  # last resort so one platform can't break the others
            return self._fail(f"Unexpected error: {e}")
        finally:
            if own:
                await client.aclose()

    def _fail(self, error: str) -> PlatformResult:
        return PlatformResult(platform=self.name, status="failed", error=error)


def check(resp: httpx.Response, what: str) -> dict:
    """Raise PlatformError with the API's own message on non-2xx; return JSON."""
    if resp.status_code >= 400:
        detail = resp.text[:200].replace("\n", " ")
        if resp.status_code in (401, 403):
            raise PlatformError(f"Authentication failed ({what}, HTTP {resp.status_code}): {detail}")
        raise PlatformError(f"{what} HTTP {resp.status_code}: {detail}")
    try:
        return resp.json()
    except ValueError:
        return {}
