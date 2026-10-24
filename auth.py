"""API key authentication.

Valid keys come from the SNIPURL_API_KEYS env var (comma-separated).
Falls back to a single "dev-key" for local development.
"""
import os
import secrets

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def load_api_keys():
    raw = os.environ.get("SNIPURL_API_KEYS", "dev-key")
    return {key.strip() for key in raw.split(",") if key.strip()}


def require_api_key(api_key: str = Security(api_key_header)):
    if api_key is not None:
        for valid_key in load_api_keys():
            if secrets.compare_digest(api_key, valid_key):
                return api_key
    raise HTTPException(
        status_code=401,
        detail="Missing or invalid API key",
        headers={"WWW-Authenticate": "ApiKey"},
    )
