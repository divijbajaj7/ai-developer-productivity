import os
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from auth import require_api_key
from models import ShortenRequest, ShortenResponse, StatsResponse
from ratelimit import RateLimiter, rate_limit
from storage import Storage
from service import shorten, record_visit

app = FastAPI(title="SnipURL", version="0.1.0")
store = Storage()

# Only needed when the ui/ files are served from a different origin than the API.
cors_origins = os.environ.get(
    "SNIPURL_CORS_ORIGINS", "http://localhost:5500,http://127.0.0.1:5500"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in cors_origins.split(",") if o.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
    expose_headers=["Retry-After"],
)

shorten_limiter = RateLimiter(limit=10, window_seconds=60)
redirect_limiter = RateLimiter(limit=60, window_seconds=60)
stats_limiter = RateLimiter(limit=30, window_seconds=60)

# Serve the front end from the same origin as the API. These must be
# registered before the catch-all /{code} route below.
UI_DIR = Path(__file__).parent / "ui"
app.mount("/ui", StaticFiles(directory=UI_DIR), name="ui")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(UI_DIR / "index.html")


@app.post(
    "/shorten",
    response_model=ShortenResponse,
    dependencies=[Depends(require_api_key), Depends(rate_limit(shorten_limiter))],
)
def create_short_url(req: ShortenRequest):
    code = shorten(store, req.url)
    base = os.environ.get("SNIPURL_BASE_URL", "http://snip.url").rstrip("/")
    return ShortenResponse(code=code, short_url=f"{base}/{code}")


@app.get("/{code}", dependencies=[Depends(rate_limit(redirect_limiter))])
def redirect_to_url(code: str):
    long_url = store.get_url(code)
    if long_url is None:
        raise HTTPException(status_code=404, detail="Code not found")
    store.increment_clicks(code)
    record_visit(code)
    return RedirectResponse(long_url)


@app.get(
    "/stats/{code}",
    response_model=StatsResponse,
    dependencies=[Depends(require_api_key), Depends(rate_limit(stats_limiter))],
)
def get_stats(code: str):
    long_url = store.get_url(code)
    if long_url is None:
        raise HTTPException(status_code=404, detail="Code not found")
    return StatsResponse(
        code=code,
        long_url=long_url,
        clicks=store.get_clicks(code),
    )
