# SnipURL Architecture

> Each diagram is Mermaid source followed by a pre-rendered SVG in `docs/diagrams/`,
> so it is visible even in viewers that don't render Mermaid. Regenerate the SVGs
> if you change the diagrams.

SnipURL is a small URL shortener built with FastAPI. A single process holds
all state in memory.

## Component overview

```mermaid
flowchart LR
    Client([HTTP client])

    subgraph App["FastAPI app (main.py)"]
        direction TB
        Routes["Routes<br/>POST /shorten<br/>GET /code<br/>GET /stats/code"]
        Auth["auth.py<br/>require_api_key"]
        RL["ratelimit.py<br/>RateLimiter + rate_limit()"]
        Svc["service.py<br/>shorten, encode_base62,<br/>record_visit"]
        Models["models.py<br/>Pydantic schemas"]
        Store[("storage.py<br/>Storage (in-memory)")]
    end

    Env[/"SNIPURL_API_KEYS<br/>env var"/]

    Client --> Routes
    Routes -- "validates with" --> Models
    Routes -- "Depends" --> Auth
    Routes -- "Depends" --> RL
    Auth -. "reads keys" .-> Env
    Routes --> Svc
    Routes --> Store
    Svc --> Store
```

![Component overview](diagrams/components.svg)

| Module | Responsibility |
|---|---|
| `main.py` | Creates the app and one shared `Storage`; declares routes and wires auth and rate-limit dependencies. |
| `models.py` | Request and response schemas (`ShortenRequest`, `ShortenResponse`, `StatsResponse`). |
| `service.py` | Business logic: ID to base-62 code, saving a URL, visit log. |
| `storage.py` | In-memory maps for URLs and click counts, plus the ID counter. |
| `auth.py` | `X-API-Key` header check against `SNIPURL_API_KEYS` (default `dev-key`). |
| `ratelimit.py` | In-memory sliding-window limiter, keyed per API key or client IP. |

## Request pipeline

Dependencies on a route run in the order listed, so authentication happens
before rate limiting. A request with a bad key is rejected with 401 and never
counts against a limit.

```mermaid
flowchart TD
    A([Request]) --> B{Route needs<br/>API key?}
    B -- "yes: /shorten, /stats" --> C{Valid<br/>X-API-Key?}
    C -- no --> X401[/"401 Unauthorized"/]
    C -- yes --> D
    B -- "no: GET /code" --> D{Under rate limit<br/>for this identity?}
    D -- no --> X429[/"429 + Retry-After"/]
    D -- yes --> E{Body valid?<br/>POST only}
    E -- no --> X422[/"422 Validation error"/]
    E -- yes --> F[Run handler]
    F --> G([Response])
```

![Request pipeline](diagrams/request-pipeline.svg)

## Flow: shorten a URL

```mermaid
sequenceDiagram
    participant C as Client
    participant M as main.py
    participant S as service.shorten
    participant D as Storage

    C->>M: POST /shorten {url}
    M->>M: require_api_key, rate_limit
    M->>S: shorten(store, url)
    S->>D: next_id()
    D-->>S: n (1, 2, 3, ...)
    S->>S: code = encode_base62(n)
    S->>D: save(code, url)
    S-->>M: code
    M-->>C: 200 {code, short_url}
```

![Shorten a URL sequence](diagrams/shorten-sequence.svg)

## Flow: follow a short link

```mermaid
sequenceDiagram
    participant C as Client
    participant M as main.py
    participant D as Storage
    participant S as service

    C->>M: GET /{code}
    M->>M: rate_limit (no API key needed)
    M->>D: get_url(code)
    D-->>M: long_url (or None, then 404)
    M->>D: increment_clicks(code)
    M->>S: record_visit(code)
    M-->>C: 307 redirect to long_url
```

![Follow a short link sequence](diagrams/redirect-sequence.svg)

## Design notes and limits

- **Single process only.** Storage and rate-limit counters live in process
  memory. Running more than one instance gives each its own codes, clicks and
  limits. The code comments suggest Redis or Postgres for production.
- **Restart loses everything.** Nothing is persisted.
- **Rate-limit identity.** Calls with an `X-API-Key` header are limited per key;
  others per client IP (`request.client.host`).
- **Short URL host** comes from `SNIPURL_BASE_URL` (default `http://snip.url`).

## Known issues

All previously listed bugs are fixed: click counting, unknown codes (now 404),
`encode_base62(0)`, the unbounded visit log, URL validation (http/https only),
and the rate-limit bypass with fake keys. Remaining limits are the design
notes above (single process, no persistence, sequential guessable codes).
