# SnipURL UI

Static landing page + shortener for the SnipURL API. Plain HTML, Tailwind (CDN) and vanilla JS — no build step.

## Run it

The FastAPI app serves this folder itself, so there is only one server:

```bash
uvicorn main:app --reload    # from the repo root
```

Open http://127.0.0.1:8000 and hit **Get Started**. The UI is at `/`, its assets under `/ui/`, and the API docs at `/docs`.

## Deploying

On Vercel the same `main.py` app is deployed as a Python function (FastAPI preset), so the UI and API share one URL.
Set `SNIPURL_API_KEYS` in the Vercel project if you want a key other than `dev-key` (and update `config.js` to match).
Note: storage is in memory, so on serverless links can disappear when an instance is recycled.

## Configuration

- `ui/config.js` — `API_BASE` (leave empty when served by the API; set it only if you host `ui/` on another origin) and `API_KEY` (must be one of `SNIPURL_API_KEYS`; defaults to `dev-key`).
- If you do host `ui/` separately, add its origin to `SNIPURL_CORS_ORIGINS`.

## Files

| File | Purpose |
| --- | --- |
| `index.html` | Landing page, shortener panel, features, pricing, footer |
| `styles.css` | Red-noir theme: animations, shiny CTA, stars, focus & reduced-motion styles |
| `app.js` | URL validation, API calls, result/stats rendering, copy, recent links (localStorage) |
| `config.js` | API base URL and key |
