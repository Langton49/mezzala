# Mezzala — Soccer Dashboard: Project Context

> **Purpose of this document:** written for an AI coding agent picking up this project mid-build. It captures current architecture, the reasoning behind non-obvious decisions, what's actually implemented vs. designed-only, and known gotchas. Read in full before making changes. This file was fully rewritten on 2026-10-01 — the previous version described a much earlier, pre-frontend, pre-deployment snapshot of the project and was badly stale; don't trust cached knowledge of this file from before that date.
>
> **Current state in one line:** MVP is built and **deployed to production** — frontend on Vercel, backend + poller + Postgres + Redis on Railway, CI (GitHub Actions) gating every merge to `main` via required PR checks.

---

## 1. Project Summary

A live soccer dashboard: fixtures (by matchday or by date), standings with zone highlighting, and player stat leaderboards, across major European leagues and cup competitions, with near-real-time score/minute updates for in-progress matches. No news/RSS feature was ultimately built despite earlier design work (see §11). No user accounts/auth — fully public, read-only.

---

## 2. Tech Stack (current, verified against source)

| Layer | Choice | Notes |
|---|---|---|
| Backend framework | **FastAPI** (Python 3.14, async) | Stateless REST + one WebSocket route (`/ws/live`). No auth, CORS wide open (`allow_origins=["*"]`) — fine today since nothing is auth-gated or mutating. |
| Poller | **Standalone Python process** (`poller/poller.py`) | Singleton — must never be replicated (would multiply API calls and cause racing writes). Run via `python -m poller.poller`. Uses `APScheduler` (`AsyncIOScheduler`). |
| Config | **pydantic-settings** (`config/settings.py`) | All 7 fields required, no defaults — app fails fast at import time if any env var is missing. Field names must match `.env` keys exactly (case-insensitive only). |
| Database | **Postgres** | Source of truth. SQLAlchemy 2.0 async ORM, `asyncpg` driver at runtime. |
| Migrations | **Alembic** | `database/migrations/`. Runs with a **separate sync driver** (`psycopg2-binary`) — `env.py` strips `+asyncpg` from the configured URL at runtime via `settings.db_url.replace("+asyncpg", "")`. `psycopg2-binary` must be in `requirements.txt` even though nothing imports it literally — SQLAlchemy resolves it dynamically from the bare `postgresql://` URL scheme, so a plain grep for `import psycopg2` won't find this dependency (this exact gap caused a production outage — see §13). |
| Cache / pub-sub | **Redis** | One job only, currently: pub/sub fan-out of live fixture changes (`poll_live_fixtures` publishes to channel `match-updates`, `backend/app/redis_listener.py` subscribes and relays to WebSocket clients). The response-caching use case from early design docs was never implemented — standings/stats are read straight from Postgres on every request, no Redis cache layer exists for them. |
| Frontend | **Next.js 16 (App Router), React 19, Tailwind v4** | Fully built, fully client-rendered (`"use client"` throughout) — no ISR, no server components doing data fetching. A single-page dashboard, not a multi-route site (`app/page.tsx` renders one `<DashboardShell/>`). |
| Local dev infra | **Docker Compose** (Postgres + Redis only) | `docker-compose.yml`, project root. |
| HTTP client (poller) | **`httpx`** (fully async) | No synchronous-library remnants. |
| Dev orchestration | Root `package.json` + `concurrently` | `npm run dev` from repo root runs poller + backend + frontend together. Root `package-lock.json` exists alongside `frontend/package-lock.json` — intentional (see `frontend/next.config.ts`'s `turbopack.root` override, added to resolve Next.js's workspace-root ambiguity warning). |

**Explicitly NOT part of the current stack**, despite appearing in earlier design docs: API-Football (dropped — no field for it in `Settings` anymore), TheSportsDB (team/league/player images are sourced from **bzzorio's own image API** instead, see §3), `feedparser`/RSS ingestion (the package is installed and `config/news_feeds.py` has a static dict of feed URLs, but no ingestion code was ever built — it's inert), openfootball/StatsBomb historical data (never started).

---

## 3. Data Source — bzzorio

**bzzorio** (`sports.bzzoiro.com` — yes, the code spells it `bzzorio`, the domain is `bzzoiro`; this is a deliberate, consistent internal spelling across the whole codebase, not a typo to "fix") is the **sole** live-data source. It provides fixtures (live/upcoming/by-date), standings, stat leaders (scorers/assists/yellow/red cards/fouls), competition stage/round metadata, and team/league/player crest images.

- **API base path includes a version prefix**: `BZZORIO_BASE_URL` must be `https://sports.bzzoiro.com/api/v2/`, **not** the bare domain. Using the bare domain silently 404s on every actual data route while the root `/` and `/docs/` still return 200 (since those don't need the prefix) — this exact mistake caused a multi-hour debugging detour in production (chased as a phantom IP-block before the real cause was found — see §13).
- **Auth**: `Authorization: Token <BZZORIO_API_KEY>` header, plain (no quotes — if your local `.env` has the key quoted, note that `python-dotenv` strips quotes automatically but a platform's raw env-var UI (e.g. Railway) usually does not, so copy the *unquoted* value when setting it elsewhere).
- **Images**: `lib/images.ts` (frontend) builds URLs like `https://sports.bzzoiro.com/img/{team|league|player}/{id}/?bg=transparent` (player adds `sor=true`). A valid id with no image returns **204, not 404** — `components/common/Logo.tsx` handles this via the `<img>`'s `onError` handler (not `next/image`, deliberately — needed for the onError fallback to work against this provider's behavior), falling back to an inline SVG placeholder and caching the failure in `sessionStorage` per session so it doesn't re-flicker on remount.
- **Known data gap, accepted, not a bug to fix**: bzzorio's `status` field for a fixture is passed through unvalidated (`transform_fixture` in `database/repository.py`). Observed values include `notstarted`, `inprogress` (not `"live"` — a wrong assumption cost real debugging time earlier in this project's history), `finished`, `postponed`, and `unresolved` (fixtures with a past `event_date` and null scores — a genuine upstream data gap with no clean resolution; the frontend currently just falls back to showing the scheduled kickoff time for these).
- **Known data gap, accepted**: standings zone data (`zone_key`/`zone_label`/`zone_type`) sometimes omits a team's zone even when the position falls inside the legend's stated range. Documented, deliberately left as-is.
- **Nations League (league id 64) doesn't return a flat `standings` list** the way domestic leagues do — `fetch_standings` in `poller.py` catches this via `except (KeyError, TypeError)` and logs a contained message per-poll; this is expected, recurring, harmless log noise, not a crash.

`config/leagues.py`'s `LEAGUES` dict is the single source of truth for which competitions the poller tracks (currently 16: 6 domestic leagues, 2 domestic cups × 3 countries minus gaps, 4 UEFA competitions — see the file directly for the exact list). Each entry has `bzzorio_id`, `name`, `country`, `type` (`"league"` or `"cup"`). **Known typo preserved in the dict key** (not the data): the Championship's key is `"champoinship"` — harmless since nothing keys off that string externally, but don't "fix" it without checking nothing depends on the misspelling.

**The frontend does NOT read this dict.** `frontend/components/sidebar/LeagueList.tsx` hand-maintains its own separate `PLACEHOLDER_LEAGUES` array (id + display name only, no backend call). **This is a known, accepted drift risk** — if a league is added/removed/renamed in `config/leagues.py`, the frontend list has to be updated by hand or it silently goes stale (a real instance of this was caught and fixed once already: Carabao Cup/EFL Cup, id 40, was missing from the frontend list for a while after being present in the backend config the whole time). A proper fix would be a backend endpoint exposing the league list dynamically — not built, flagged as a good next step.

---

## 4. Architecture — Data Flow

```
bzzorio API → poller (singleton) → Postgres (always, every cycle)
                                  → Redis "match-updates" channel (only on actual change)

Postgres → backend (REST, read-only, never calls bzzorio itself)
Redis    → backend (redis_listener.py subscribes) → ConnectionManager → WebSocket clients

frontend: REST poll (useJsonFetch, pollMs) for baseline freshness
        + WebSocket (useLiveUpdates / useLiveMergedFixtures) for instant patches in between polls
```

### Principles that hold today (verified, not aspirational):
1. **Only the poller writes fixture/standings/stat data.** No route handler writes to any of these tables.
2. **Postgres is truth; Redis is "what just changed."** Every `poll_live_fixtures` cycle UPSERTs to Postgres regardless of whether anything changed (`matches_changed()` + `LIVE_MATCHES_STORE` in-memory dict gates the Redis publish only, not the Postgres write).
3. **The poller is a singleton, always.**
4. **Backend instances are stateless** — one is running in production today; horizontal scaling isn't provisioned (not needed at current traffic).

### What differs from early design docs (if you find older notes, trust this instead):
- **No ISR, no server-rendered pages with revalidation.** The frontend is a single fully-client-rendered page. Freshness comes from REST polling (`useJsonFetch`'s `pollMs` param, 20s on fixture views) plus the WebSocket layer for instant live-score patches, not from Next.js's caching model.
- **`ConnectionManager` (`backend/app/connection_manager.py`) is a flat broadcast-to-all**, not the inverted per-league-subscriber-index design from early docs. `/ws/live`'s `leagues` query param is accepted but **unused** — every connected client gets every match-update regardless of league. This is a known, deliberate simplification (the frontend's own merge logic already discards updates for fixtures not currently in view, so the only cost is wasted bandwidth, not correctness) — revisit if traffic ever makes this matter.
- **`poll_stages`/`poll_standings`/`poll_stat` are event-triggered, not on a fixed timer.** `poll_live_fixtures` (every 30s) detects a fixture transitioning to `"finished"` for the first time and fires `poll_stages_then_stats(league_id)` for just that league. All three also run once at poller startup (`poll_seed_missing_seasons()` + `poll_stages_then_stats()` in `main()`) so a fresh deploy isn't empty while waiting for the first match to finish. **Ordering matters here**: `poll_standings`/`poll_stat` both resolve a season id via `comp_stages` (written by `poll_stages`), so `poll_stages_then_stats()` deliberately `await`s `poll_stages()` to completion before firing the other two — firing all three as independent concurrent tasks is a real race that's invisible on any DB that already has stage data (which is every local dev DB, ever) and fails deterministically on a genuinely empty one (this exact bug shipped once, caught immediately via Railway's fresh-DB logs — see §13).

---

## 5. Config Layer (`config/settings.py`)

```python
class Settings(BaseSettings):
    bzzorio_api_key: str
    bzzorio_base_url: str
    db_url: str
    redis_url: str
    postgres_user: str
    postgres_pass: str
    postgres_db: str
    model_config = SettingsConfigDict(env_file=".env")
```

All 7 required, no `Optional` fields — missing any one raises `pydantic.ValidationError` at import time (fail-fast, this is correct behavior, not a bug). **`postgres_user`/`postgres_pass`/`postgres_db` are declared but never actually read anywhere in application code** (grepped, confirmed) — they exist only because `docker-compose.yml` needs them for local Postgres bootstrapping. They still need *some* value set wherever the app runs (Railway included) or the app won't boot, even though the value itself is functionally inert.

`.env.example` (repo root, safe to commit) documents the shape with placeholder values. `frontend/.env.example` separately documents `NEXT_PUBLIC_API_URL`/`NEXT_PUBLIC_WS_URL` — **both are baked in at Next.js build time, not read at runtime**, so they must be set in Vercel's project settings *before* the first build, not after.

---

## 6. Database Layer

```
database/
├── database.py    # async engine, async_session factory, get_session() FastAPI dependency
├── tables.py       # SQLAlchemy ORM models (Base, Fixture, CompetitionStages, Standing, PlayerStat)
├── repository.py   # ALL reads/writes go through here — no raw queries elsewhere
└── migrations/     # Alembic
```

**No separate `Team` table exists.** Team identity is denormalized directly into whichever table references it (`home_team_id`/`home_team` string pair on `Fixture`, `team_id`/`team_name` on `Standing`/`PlayerStat`) — there is no cross-provider entity-resolution layer; this was designed pre-bzzorio-pivot in very early docs and was never built, since bzzorio is the only source.

**Current schema (verified against `database/tables.py`), 4 tables:**

- **`Fixture`** (`fixtures`) — PK `id` (bzzorio's own fixture id, not autoincrement). `league_id`, `home_team_id`/`home_team`/`home_coach_id`, `away_team_id`/`away_team`/`away_coach_id`, `referee_id`, `round_number`/`round_name`/`group_name`, `stage`/`stage_name`, `venue_id`, `event_date` (`DateTime(timezone=True)` — must stay tz-aware), `status`, `home_score`/`away_score`/`current_minute`/`home_score_ht`/`away_score_ht`, `last_updated` (auto `onupdate`).
- **`CompetitionStages`** (`comp_stages`) — PK autoincrement `id`, unique on `(league_id, stage)`. `season_id`, `stage`/`stage_name`, `rounds`, `sort_order`, `start_date`/`end_date`.
- **`Standing`** (`standings`) — PK autoincrement `id`, unique on `(league_id, season_id, team_id)`. Full table stats (`played`/`won`/`drawn`/`lost`/`gf`/`ga`/`gd`/`pts`), optional xG fields, `form`, `zone_key`/`zone_label`/`zone_type`.
- **`PlayerStat`** (`player_stats`) — PK autoincrement `id`, unique on `(league_id, season_id, stat_type, player_id)`. `stat_type` is one of `scorers`/`assists`/`yellowcards`/`redcards`/`fouls`.

**`repository.py` conventions:**
- Every `upsert_*` function (`upsert_fixtures`, `upsert_stages`, `upsert_standings`, `upsert_stat`) takes a **`list[dict]`** and loops internally — callers must pass the full batch, not call it once per item (a mismatch here caused a real production crash once, see §13).
- `transform_*` functions (`transform_fixture`, `transform_stage`, `transform_standings`, `transform_stat`) convert raw bzzorio JSON into the dict shape `upsert_*` expects — always call these before upserting, never pass raw API JSON through directly.
- `get_current_stage(db, league_id)` returns `None` (not an exception) when a league has no seeded stage data — **callers must check for `None` explicitly**; two routes (`standings.py`, `stats.py`) originally didn't and crashed with a 500 on any unseeded/typo'd league id. Fixed, but if you add a new route using this function, remember the check.
- `has_fixtures_for_season(db, league_id)` backs the one-time seed-guard (`poll_seed_missing_seasons`) — checks for any fixture at or after `current_season_start()` for that league.
- `orm_to_dict(obj)` converts an ORM instance back to a plain dict via `inspect(obj).mapper.column_attrs` — needed since ORM objects have no `.model_dump()`.

### Migrations
- Run as `python -m alembic ...` from repo root (not bare `alembic`, not from inside `database/` — relative imports in `env.py` need repo root on the import path).
- `database/migrations/env.py` sets `config.set_main_option("sqlalchemy.url", settings.db_url.replace("+asyncpg", ""))` at module top level — this forces the **sync** `psycopg2` driver for the migration run itself, separate from the app's async `asyncpg` driver at runtime. **`psycopg2-binary` must be in `requirements.txt`** (see §2) — this is easy to miss because nothing imports it by name anywhere in the source.
- Workflow for a schema change: `python -m alembic revision --autogenerate -m "description"` → inspect the generated file → `python -m alembic upgrade head`.
- In production, migrations run automatically on every backend deploy via the Railway start command (see §8) — `alembic upgrade head` is idempotent, safe to run on every boot even when there's nothing pending.

---

## 7. Docker / Local Infra

`docker-compose.yml` (repo root) — Postgres 16 + Redis 7, named volumes, healthchecks. Containers: `mezzala_postgres`, `mezzala_redis`. Standard `docker compose up -d`; `.env` must sit next to `docker-compose.yml`. Postgres env vars only take effect on first volume init — changing credentials later needs `docker compose down -v` + `up -d` to actually apply.

---

## 8. Poller (`poller/poller.py`) — current jobs

| Job | Schedule | Notes |
|---|---|---|
| `poll_live_fixtures` | every 30s | Concurrent per-league fetch (`asyncio.TaskGroup`). Upserts regardless of change; publishes to Redis only on change (`matches_changed`); fires `poll_stages_then_stats(league_id)` when a fixture first transitions to `"finished"`. **Was 5s, then 15s, now 30s** — reduced deliberately for Railway cost (compute is metered per-second; an always-on 5s-interval worker was a meaningful chunk of the monthly bill). WebSocket delivery to the frontend is still near-instant regardless of this interval, since that's push-based off whatever the poller detects, not tied to how often it checks. |
| `poll_upcoming_matches` | daily (+ once at startup) | Rolling 7-day window, all leagues, keeps venue/referee/manager changes fresh for already-known upcoming fixtures. |
| `poll_seed_missing_seasons` | once at startup only | Guarded by `has_fixtures_for_season` — full-season backfill only for leagues with zero fixtures in Postgres (fresh DB, new season, newly-added league). Does nothing on an ordinary restart. |
| `poll_stages_then_stats` | once at startup + event-triggered | See §4 for the ordering/race-condition note. Accepts an optional `league_id` to scope to one league (event-triggered case) or `None` for all (startup case). |

`redis_client` is `redis.asyncio.from_url(settings.redis_url)` — **must stay async and must use `settings.redis_url`**, not a hardcoded `localhost` sync client. This exact regression shipped once (worked fine locally where Redis genuinely is on localhost; broke silently in any non-local deployment) — see §13.

`client` (the bzzorio httpx client) is created once at module level with `base_url=settings.bzzorio_base_url` and the auth header baked in — every `fetch_*` function just does relative-path `client.get("events/live/", ...)` calls against it.

---

## 9. Backend (`backend/`)

```
backend/
├── app/
│   ├── main.py              # FastAPI app, CORS, lifespan (starts redis_listener)
│   ├── connection_manager.py # flat broadcast-to-all WebSocket manager
│   └── redis_listener.py     # subscribes to "match-updates", relays to ConnectionManager
├── connection_manager/routes/
│   ├── matches.py            # /matches/..., /ws/live
│   ├── standings.py          # /standings/{league_id}
│   └── stats.py              # /stats/{league_id}/{stat}
└── types/types.py            # Pydantic response models (FixtureOut, StandingsOut, StatOut)
```

Routes are thin — they call `repository.py` functions directly and return ORM results (FastAPI's `response_model` handles serialization via `from_attributes=True` on each `*Out` model). Path params are typed directly (`league_id: int`, `date: datetime.date`) so FastAPI/Pydantic validates automatically and returns a clean `422` on bad input — **don't** manually `int(...)`/`datetime.fromisoformat(...)` a path param inside a route body, that bypasses this and turns bad input into an unhandled 500 (this exact pattern existed in `matches.py` and was fixed).

`GET /` is a bare health check (`{"status": "ok"}`), used by both manual checks and worth knowing about if adding uptime monitoring later.

---

## 10. Frontend (`frontend/`)

Next.js App Router, fully client-rendered, Tailwind v4. No routing beyond the single page — "navigation" is all client state (league, tab, matchday/date, sub-view), persisted to the **URL query string** so reload/share/bookmark preserves it (`?league=7&tab=standings&round=5` etc.) — implemented via `context/DashboardContext.tsx` (league + tab) and `hooks/useUrlParam.ts` (a small shared `useUrlParamSetter` used by `FixtureView`/`MatchdayView`/`DateView` for the sub-tab/round/date). `router.replace` throughout, never `push` — navigating doesn't fill up browser history.

**Layout**: `DashboardShell` → centered `max-w-[1200px]` band (not full-bleed) containing a `Sidebar` (a self-contained rounded-card nav, `self-start` so it doesn't stretch to viewport height — **not collapsible**, that feature was built then deliberately removed once the sidebar stopped needing to conserve width) and `MainView` (further capped to `max-w-3xl` for actual content — fixture rows/standings table/stat cards all render at a fixed reading width regardless of viewport, by design, after an explicit decision that a wide, mostly-empty layout read as "generic"). **No responsive/mobile support exists** — zero breakpoint classes anywhere in the codebase, fixed-width sidebar; acceptable only if this stays a desktop-only tool.

**Data fetching**: `hooks/useJsonFetch.ts` is the single shared fetch hook (loading/error/stale-data handling for every view). Key behaviors, each added for a specific reason — don't simplify without understanding why:
- Optional `pollMs` param for background refresh (fixture views poll every 20s) without flipping `loading` back to true.
- A fetch failure sets an `error` flag but **does not clear existing data** — a transient poll failure shouldn't blank out a perfectly good list already on screen. Views render a distinct `ErrorState` (not `EmptyState`) only when there's an error *and* nothing to show.
- A non-2xx response is treated as an error (checks `res.ok` before parsing), not handed through as if it were valid data — otherwise a backend 500 with a JSON error body would get passed to `.sort()`/`.slice()` downstream and throw at render time.
- Skeleton display is deliberately delayed (`SKELETON_DELAY_MS`, currently **600ms** — tuned against real production latency, Vercel-to-Railway round-trips typically run 280–525ms; the original 150ms was tuned against localhost where everything was sub-10ms and was far too aggressive in production, causing a skeleton flash on nearly every navigation). Below that threshold, stale-but-valid previous data just stays on screen until new data quietly replaces it.

**Live updates**: `hooks/useLiveUpdates.ts` — raw WebSocket connection to `/ws/live` (auto-reconnects on drop, no backoff beyond a flat retry delay) plus `useLiveMergedFixtures(matches)`, which patches individual fixtures into an already-fetched list the instant a WS message arrives, without waiting for the next REST poll. Only merges the 4 fields that can actually change live (`status`/`home_score`/`away_score`/`current_minute`) — the WS payload's `event_date` is serialized via Python's `str()`, not ISO 8601, so merging the whole payload would risk feeding a malformed date into date-formatting code elsewhere.

**Panel remount/animation gotcha**: `MatchdayView`/`DateView` key their content `Panel` on a `displayKey` state that only updates once new data has actually arrived (inside a `useEffect` on `matches`), **not** on the immediately-clicked `round`/`date` value. Keying directly on the navigation target caused the panel to remount (and re-trigger its entrance animation) on the very next render — while still showing the *previous* round/date's stale data — before the new fetch had resolved, producing a double-flicker on any real network latency (invisible on localhost, obvious in production). If you touch this pattern, keep the "state that drives the fetch" and "state that drives the remount key" separate.

**Images**: `components/common/Logo.tsx` + `lib/images.ts` — see §3.

**Dark mode**: a complete, retuned color palette exists in `app/globals.css` under `@media (prefers-color-scheme: dark)`, but there is **no toggle or activation mechanism** — it only applies if the OS/browser itself is in dark mode. Not wired to a user preference or class-based toggle.

**Known-unused, deliberately kept**: `components/ai_panel/AiView.tsx` exists, is not imported or rendered anywhere — kept intentionally as a stub for a future feature, not dead code to delete.

---

## 11. Deployment & CI/CD

**Hosting**: Vercel (frontend) + Railway (backend web service, poller worker service, managed Postgres, managed Redis — all in one Railway project, Hobby plan). Both platforms deploy automatically via their native GitHub App integration on every push to `main` — **GitHub Actions is not the deploy trigger**, it's a CI gate only.

**GitHub Actions** (`.github/workflows/ci.yml`): two jobs, `frontend` (npm ci → tsc → eslint → next build) and `backend` (pip install -r requirements.txt → import-check `backend.app.main` and `poller.poller`, using fake-but-syntactically-valid inline env vars since there's no real `.env` in CI and `Settings`/`create_async_engine`/`redis.from_url` are all lazy enough that a fake value never actually needs to connect to anything for an import check to pass). Triggers on `push`/`pull_request` to `main`.

**Branch protection on `main`**: requires a PR (direct pushes blocked, including from an agent), requires the `frontend`/`backend` checks to pass, requires the branch be up to date with `main` before merge. **Does not** require a review approval — this is a solo-maintainer repo and GitHub doesn't allow self-approval, so that setting would create a permanent deadlock if enabled.

**Workflow in practice**: every change, including trivial ones, goes through `git checkout -b <branch>` → commit → push → open PR on GitHub → wait for CI → merge → delete branch (both local and remote) → pull `main` locally. This is now the established, consistent pattern for this repo — don't push directly to `main` even if it were technically possible.

### Railway-specific gotchas (all hit and fixed in production, worth knowing before touching the Railway config):
- **`DB_URL` must be hand-composed**, not pasted from Railway's Postgres plugin's own `DATABASE_URL` variable (that one's plain `postgres://`, wrong scheme). Use: `postgresql+asyncpg://${{Postgres.PGUSER}}:${{Postgres.PGPASSWORD}}@${{Postgres.PGHOST}}:${{Postgres.PGPORT}}/${{Postgres.PGDATABASE}}` as a Railway variable reference.
- **`REDIS_URL`** can be referenced directly: `${{Redis.REDIS_URL}}`.
- **The backend service's public domain has its own separate "target port" setting**, which does *not* automatically track whatever `$PORT` the app actually binds to at runtime — these can mismatch (app listening on 8080, domain routing to a stale default of 8000) and produce a `502 Application failed to respond` even though the app itself is healthy and logging normally. Check this field explicitly if a freshly-generated domain 502s.
- **Backend start command** runs migrations first: `python -m alembic upgrade head && python -m uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`. **Poller start command** is just `python -m poller.poller` — no migrations, no public networking needed (it's a pure background worker, don't generate a domain for it).
- Both services' **root directory must stay the repo root**, not `backend/`/`poller/` — the app's absolute imports (`backend.app.main`, `poller.poller`) need repo root on `sys.path`, matching how everything is already invoked locally. There's no installable package structure (no `pyproject.toml`).
- `requirements.txt` (repo root) is the single dependency manifest for both Railway services — see §2/§6 for the `psycopg2-binary` gotcha specifically.

### Vercel-specific notes:
- **Root directory must be set to `frontend`** (monorepo — the Next.js app isn't at repo root).
- `NEXT_PUBLIC_API_URL`/`NEXT_PUBLIC_WS_URL` must be set in Vercel's project env vars *before* the first deploy (build-time baking, see §5). Use `wss://` not `ws://` for the WS URL — Railway serves the backend over HTTPS.

---

## 12. Change Detection (poller, in-memory)

`LIVE_MATCHES_STORE: dict[int, tuple]` at module level in `poller.py`, compared via `matches_changed()` against a `(status, home_score, away_score, current_minute)` tuple per fixture. In-memory, not Redis, not a Postgres pre-read — deliberate: the poller is a singleton so this is always the same process reading/writing it; a restart just causes one harmless over-publish burst (every live match "looks new" once), Postgres is unaffected since it's written unconditionally every cycle regardless of this check. This is also what lets `poll_live_fixtures` detect a *transition* to `"finished"` (comparing the previous stored status before the snapshot gets overwritten) to trigger `poll_stages_then_stats`.

---

## 13. Notable Bugs Hit and Fixed This Build-Out (don't reintroduce)

| Bug | Cause | Fix |
|---|---|---|
| Backend 500 on any unseeded/typo'd `league_id` | `standings.py`/`stats.py` called `get_current_stage(...).season_id` without checking for `None` | Explicit `if curr_season is None: return []` in both routes. |
| Backend 500 on bad `league_id`/date input | `matches.py` manually did `int(league_id)`/`datetime.fromisoformat(date)` in the route body, no try/except | Routes now type path params directly (`league_id: int`, `date: date`) — FastAPI validates and returns a clean 422 automatically. |
| Poller's Redis publishes silently went nowhere in production | `redis_client` was a hardcoded sync `redis.Redis(host="localhost", ...)`, ignoring `settings.redis_url` entirely — worked locally by coincidence (Redis genuinely was on localhost there) | Switched to `redis.asyncio.from_url(settings.redis_url)`, matching `redis_listener.py`'s existing correct pattern. |
| `poll_standings`/`poll_stat` threw `Exception("Season id not found")` on a fresh/empty database | Fired as independent concurrent tasks alongside `poll_stages`, racing it — invisible on any DB that already had stage data (every local dev DB by the time this was tested), deterministic failure on a genuinely empty one | New `poll_stages_then_stats()` wrapper `await`s `poll_stages()` to completion before firing the other two. |
| `upsert_standings(db, standing)`/`upsert_stat(db, stat)` crashed with a `TypeError` | Called once per individual item after a refactor, but both functions take `list[dict]` and loop internally — passing a single dict made `for pos in standings` iterate the dict's *keys* (strings), then `**pos` tried to unpack a string | Call once with the full flattened list, not once per item. |
| Production backend container crashed on every boot: `ModuleNotFoundError: No module named 'psycopg2'` | Alembic's `env.py` deliberately uses the sync driver for migrations (see §6); `psycopg2-binary` was never in `requirements.txt` since nothing imports it by literal name — it's resolved dynamically by SQLAlchemy from the bare `postgresql://` URL scheme, invisible to a text grep | Added `psycopg2-binary` to `requirements.txt`. |
| Production backend 502'd ("Application failed to respond") despite healthy logs | Railway's generated public domain had a separate, stale "target port" setting (8000) that didn't match what `$PORT` actually resolved to at runtime (8080) | Manually corrected the domain's target port in Railway's Networking settings. |
| Poller 404'd on *every* bzzorio request in production, worked fine locally | `BZZORIO_BASE_URL` was set from `.env.example`'s stale value (bare domain, no `/api/v2/` prefix) rather than verified against the actual working local `.env` — wasted real time chasing a wrong "datacenter IP blocking" theory (region-switching and auth-header testing both correctly ruled out, since those genuinely weren't it) before the real cause was found | Corrected to `https://sports.bzzoiro.com/api/v2/` in both `.env.example` and the Railway env vars. |
| Double-flicker navigating matchdays/dates in production (not reproducible locally) | `Panel`'s remount `key` was tied directly to `round`/`date`, which updates synchronously on click, before the new fetch resolves — remounted (and re-animated) the stale previous content immediately, then again when a skeleton kicked in after the (too-short, localhost-tuned) delay threshold | Decoupled the remount key into separate `displayKey` state that only updates once new data actually arrives; separately raised `SKELETON_DELAY_MS` from 150ms to 600ms to match real production latency (see §10). |
| `.gitignore` had a bare `migrations/` entry | Matched `database/migrations/` too (unscoped), which would have silently excluded any *future* Alembic migration file from `git add -A` | Removed the line. |

---

## 14. Known Limitations / Deliberately Deferred (not bugs — conscious scope cuts)

- **No tests** (pytest or otherwise), **no monitoring** (Sentry or otherwise), **no CI for the poller's actual runtime behavior** beyond an import-check.
- **No mobile/responsive frontend support** at all.
- **Frontend league list is hand-synced** against `config/leagues.py`, not fetched — see §3.
- **`/ws/live`'s per-league filtering is unimplemented** — flat broadcast to all clients, see §4.
- **No news/RSS feature** despite `feedparser` being installed and `config/news_feeds.py` existing — never wired up.
- **No TheSportsDB/openfootball/StatsBomb integration** — all were early-design aspirations, bzzorio covers images directly instead, historical seed data and advanced analytics were never started.
- **Standings zone data gaps and the `"unresolved"` fixture status** — genuine upstream data quirks, documented in §3, not fixable from this codebase.
- **Dark mode CSS exists but has no activation toggle** — OS-preference-only.

---

## 15. Suggested Next Steps (if picking this up fresh)

1. If extending the league list, do it in **both** `config/leagues.py` and `frontend/components/sidebar/LeagueList.tsx`'s `PLACEHOLDER_LEAGUES` — or better, finally build the backend endpoint that would let the frontend fetch this dynamically and retire the drift risk for good.
2. If adding tests, the backend/poller side (pure functions like `transform_*`, `matches_changed`) is the highest-value, lowest-effort starting point — no live DB/API needed for those.
3. If mobile support becomes a priority, the shell (`DashboardShell`/`Sidebar`/`MainView`) needs real breakpoint handling from scratch — nothing partial exists to build on.
4. Any new Railway service from this repo needs its root directory left at repo root and its start command set explicitly — Railway's auto-detection has no way to guess a multi-service monorepo's correct entry point.

---

*This document reflects a snapshot as of 2026-10-01, right after the MVP hardening pass and first production deployment. Keep it updated as the project evolves — a stale version of this file is actively misleading, not just unhelpful.*
