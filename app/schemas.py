import re
from typing import Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

from app.config import MAX_MESSAGE_LENGTH

# Anything that looks like a link: scheme://..., or a bare www. host
URL_PATTERN = re.compile(r"(?:https?://|www\.)[^\s]+", re.IGNORECASE)
TRAILING_PUNCT = ".,;:!?)]}\"'"


def extract_links(text: str) -> list[str]:
    return [m.group(0).rstrip(TRAILING_PUNCT) for m in URL_PATTERN.finditer(text)]


def is_valid_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    return (
        parsed.scheme in ("http", "https")
        and "." in host
        and not host.startswith(".")
        and not host.endswith(".")
        and " " not in url
    )


class PostingRequest(BaseModel):
    message: str = Field(..., description="Message (max 200 chars) with exactly one CTA link")

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Message must not be empty")
        if len(v) > MAX_MESSAGE_LENGTH:
            raise ValueError(f"Message must not exceed {MAX_MESSAGE_LENGTH} characters (got {len(v)})")
        links = extract_links(v)
        if len(links) != 1:
            raise ValueError(f"Message must contain exactly one CTA link (found {len(links)})")
        if not is_valid_url(links[0]):
            raise ValueError(f"Invalid URL: {links[0]} (must be http(s) with a valid host)")
        return v

    @property
    def link(self) -> str:
        return extract_links(self.message)[0]


class PlatformResult(BaseModel):
    platform: str
    status: str  # "success" | "failed"
    posted_url: Optional[str] = None
    public_access: bool = False
    date: Optional[str] = None
    time: Optional[str] = None
    error: Optional[str] = None


class PostingResponse(BaseModel):
    success: bool
    results: list[PlatformResult]
