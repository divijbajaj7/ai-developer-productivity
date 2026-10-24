from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from auth import require_api_key
from models import ShortenRequest, ShortenResponse, StatsResponse
from ratelimit import RateLimiter, rate_limit
from storage import Storage
from service import shorten, record_visit

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="SnipURL", version="0.1.0")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
store = Storage()

shorten_limiter = RateLimiter(limit=10, window_seconds=60)
redirect_limiter = RateLimiter(limit=60, window_seconds=60)
stats_limiter = RateLimiter(limit=30, window_seconds=60)


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.post(
    "/shorten",
    response_model=ShortenResponse,
    dependencies=[Depends(require_api_key), Depends(rate_limit(shorten_limiter))],
)
def create_short_url(req: ShortenRequest):
    code = shorten(store, req.url)  # NOTE: no validation that req.url is a real URL
    return ShortenResponse(code=code, short_url=f"http://snip.url/{code}")


@app.get("/{code}", dependencies=[Depends(rate_limit(redirect_limiter))])
def redirect_to_url(code: str):
    long_url = store.get_url(code)
    store.increment_clicks(code)
    record_visit(code)
    return RedirectResponse(long_url)  # BUG: unknown code -> long_url is None; should return 404


@app.get(
    "/stats/{code}",
    response_model=StatsResponse,
    dependencies=[Depends(require_api_key), Depends(rate_limit(stats_limiter))],
)
def get_stats(code: str):
    return StatsResponse(
        code=code,
        long_url=store.get_url(code),
        clicks=store.get_clicks(code),
    )
