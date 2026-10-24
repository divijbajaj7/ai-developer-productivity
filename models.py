from urllib.parse import urlparse

from pydantic import BaseModel, field_validator


class ShortenRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def url_must_be_http(cls, v):
        parsed = urlparse(v.strip())
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("url must be a valid http or https URL")
        return v.strip()


class ShortenResponse(BaseModel):
    code: str
    short_url: str


class StatsResponse(BaseModel):
    code: str
    long_url: str
    clicks: int
