# SnipURL API Reference

Base URL when run locally: `http://127.0.0.1:8001` (any port you pass to
`uvicorn`). Interactive docs are served at `/docs` (Swagger UI) and
`/openapi.json`.

## Authentication

`POST /shorten` and `GET /stats/{code}` require an API key in the
`X-API-Key` header. `GET /{code}` is public.

- Valid keys come from the `SNIPURL_API_KEYS` environment variable
  (comma-separated). If it is unset, the only valid key is `dev-key`.
- Keys are compared with a constant-time check.
- A missing or wrong key returns `401` with `WWW-Authenticate: ApiKey`.

```bash
export SNIPURL_API_KEYS="key-one,key-two"
```

## Rate limits

Sliding window, per process, 60 seconds:

| Endpoint | Limit |
|---|---|
| `POST /shorten` | 10 requests |
| `GET /{code}` | 60 requests |
| `GET /stats/{code}` | 30 requests |

Each endpoint has its own counter. The caller is identified by API key if the
header holds a valid key, otherwise by client IP. When exceeded the API returns `429`
with a `Retry-After` header (seconds).

---

## `POST /shorten`

Create a short code for a URL. Requires API key.

**Request body** (`application/json`)

| Field | Type | Required | Notes |
|---|---|---|---|
| `url` | string | yes | Must be an `http` or `https` URL with a host. |

**Response `200`**

| Field | Type | Notes |
|---|---|---|
| `code` | string | Base-62 code. The first codes are `b`, `c`, `d`, ... |
| `short_url` | string | `{SNIPURL_BASE_URL}/{code}`; the base defaults to `http://snip.url`. |

**Example**

```bash
curl -X POST http://127.0.0.1:8001/shorten \
  -H "X-API-Key: dev-key" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

```json
{"code": "b", "short_url": "http://snip.url/b"}
```

**Errors:** `401` bad or missing key, `422` missing, invalid or non-http(s) `url`,
`429` rate limited.

---

## `GET /{code}`

Redirect to the stored URL. Public (no key). Also increments the click count.

**Path parameter:** `code`, the short code.

**Response `307`** with `Location: <long url>`.

```bash
curl -i http://127.0.0.1:8001/b
```

```
HTTP/1.1 307 Temporary Redirect
location: https://example.com
```

**Errors:** `404` unknown code, `429` rate limited.

---

## `GET /stats/{code}`

Return the stored URL and click count for a code. Requires API key.

**Response `200`**

| Field | Type | Notes |
|---|---|---|
| `code` | string | Echo of the path parameter. |
| `long_url` | string | The stored URL. |
| `clicks` | integer | Number of redirects served. |

```bash
curl http://127.0.0.1:8001/stats/b -H "X-API-Key: dev-key"
```

```json
{"code": "b", "long_url": "https://example.com", "clicks": 0}
```

**Errors:** `401` bad or missing key, `404` unknown code, `429` rate limited.
---

## Status code summary

| Code | Meaning |
|---|---|
| 200 | Success (`/shorten`, `/stats`) |
| 307 | Redirect (`/{code}`) |
| 401 | Missing or invalid API key |
| 422 | Request body failed validation |
| 429 | Rate limit exceeded; see `Retry-After` |
| 404 | Unknown code on `/{code}` or `/stats/{code}` |

## Routing note

`/stats/{code}` has two path segments, so it never collides with `/{code}`.
A request to exactly `/stats` is treated as a redirect lookup for the code
`stats`.
