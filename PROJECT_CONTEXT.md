# Mezzala — Soccer Dashboard: Project Context

> **Purpose of this document:** this file is written for an AI coding agent (e.g. Claude Code) picking up this project mid-build. It captures every architectural decision, the reasoning behind it, the current implementation state, known bugs already fixed, and what's left to build. Read this in full before making changes — several early decisions (naming conventions, table design, provider abstraction) constrain how new code should be written.

---

## 1. Project Summary

A live soccer dashboard: real-time scores, standings, and curated news, built as a portfolio-grade, professionally-architected project (explicitly not a toy/internship-tier app — this shaped several stack decisions below). Original target was an MVP within one week; the project is now past the initial scaffolding phase and into core pipeline implementation.

---

## 2. Tech Stack (current, confirmed)

| Layer | Choice | Notes |
|---|---|---|
| Backend framework | **FastAPI** (Python, async) | Originally scoped for Go, deliberately switched to Python while the developer learns Go. Architecture was drawn up language-agnostic first specifically so this swap cost nothing structurally. |
| Poller | **Standalone Python process** (not part of FastAPI app) | Singleton — must never be replicated. Uses `APScheduler` (`AsyncIOScheduler`) for multi-interval job scheduling. |
| Config | **pydantic-settings** | Typed, validated `.env` loading. See §5. |
| Database | **Postgres** | Source of truth. Accessed via SQLAlchemy 2.0 async ORM. |
| Migrations | **Alembic** | Autogenerate workflow. See §6. |
| Cache / pub-sub | **Redis** | Two distinct jobs: (a) pub/sub fan-out for live score pushes to WebSocket clients, (b) response caching for expensive/slow-changing data (standings, stat leaders). |
| Frontend | **Next.js (App Router)** — not yet built | ISR-cached pages for standings/news; a client component for the live scoreboard opens its own WebSocket directly to FastAPI, bypassing the page cache entirely. |
| Local dev infra | **Docker Compose** (Postgres + Redis) | See §7. |
| HTTP client (poller) | **`httpx`** (async) — mid-migration | Original code used the synchronous `requests` library inside `async def` functions, which silently blocked the event loop. Flagged for replacement; may not be fully migrated yet — check `poller/poller.py` for current state. |
| RSS parsing | **`feedparser`**, with **`xml.etree.ElementTree`** fallback | Needed because BBC's `<media:thumbnail>` tag isn't reliably surfaced by `feedparser` for this feed. |

---

## 3. Data Sources — Decisions and Status

| Source | Status | Role |
|---|---|---|
| **API-Football** | Original primary choice; reference implementation for status codes, coverage flags. `API_FOOTBALL_KEY` still in `.env` but marked `Optional` — **not currently the active source in poller code**. | Fallback / potential primary if bzzoiro doesn't hold up. |
| **bzzoiro** (`sports.bzzoiro.com`) | **Currently the active live-data source** the poller is built against. Found by the developer, evaluated, chosen to build against first. | Live fixtures, upcoming fixtures, standings, stat leaders (scorers/assists/cards/fouls). |
| **TheSportsDB** | Planned, not yet implemented. | Team crests/logos (v2 API, `X-API-KEY` header — use this over v1). |
| **openfootball** (GitHub) | Planned, not yet implemented. | One-time historical seed data only — no live use, no API, just raw JSON files. |
| **StatsBomb open data** (GitHub) | Planned, post-MVP stretch goal. | Event-level analytics feature (only covers select open-sourced competitions, not comprehensive). Requires attribution if published. |
| **football-data.co.uk**, **Sportmonks** | Evaluated, **deliberately not used** — redundant with API-Football/bzzoiro. | — |
| **FotMob (unofficial scraper)** | **Explicitly rejected.** FotMob's ToS prohibits scraping/reproduction for any purpose. Flagged as a real legal risk, not a style preference — do not reintroduce this source. | — |

**Known risk, accepted but should stay visible to future contributors:** bzzoiro is an unproven, apparently single-operator service with no independent track record, and its business is adjacent to gambling products (links to Gamdom, sells betting-odds data). It has a genuinely strong free tier and built-in WebSocket support that could eventually replace parts of this project's own infrastructure — but it is being evaluated, not fully trusted yet. Don't assume it's a permanent dependency when refactoring.

**API-Football free tier constraint (context for why bzzoiro is being trialed):** 100 requests/day, which a 15s poll loop exhausts in ~25 minutes. Pro tier ($19/mo) removes this entirely (~1,440 req/day at 15s intervals on a normal matchday, against a 7,500/day cap).

---

## 4. Architecture — Data Flow

Full path: **raw provider API → normalize → Postgres (write) + Redis (publish, conditional) → REST (cached reads) + WebSocket (live push) → Next.js (ISR pages + client-side live component) → browser.**

### Core principles established (do not violate when extending):
1. **Only the poller writes match data.** No route handler, script, or other process is allowed to write to the `fixtures` table.
2. **Postgres is truth; Redis is "what just changed."** Every poll cycle UPSERTs to Postgres regardless of whether anything changed. Redis only gets a publish when a diff is actually detected (see §9).
3. **Normalize once, per provider.** Each provider's raw response shape is converted into one internal shape immediately on ingestion — nothing downstream should ever see provider-specific field names or status codes.
4. **The poller is a singleton, always.** Never scale it horizontally — doing so would multiply API calls against the daily quota and cause duplicate/racing writes.
5. **FastAPI instances are stateless and horizontally scalable**, sitting behind a load balancer (not yet provisioned — single instance for MVP, documented as a deliberate future step, not week-one work).
6. **WebSocket clients never talk to Redis directly** — only backend instances subscribe to Redis; each instance fans out to its own locally-connected clients via an in-memory `ConnectionManager`.

### WebSocket hub design (not yet implemented — see §11 for what's built vs. pending)
- One `redis_listener()` background task per FastAPI instance, started once via the `lifespan` context manager at app boot — not per-connection, not per-request.
- `ConnectionManager` uses an **inverted index** for O(k) broadcast instead of O(n) scanning:
  - `connections: dict[conn_id, WebSocket]`
  - `client_leagues: dict[conn_id, set[league_id]]` (for cleanup)
  - `league_subscribers: dict[league_id, set[conn_id]]` (for lookup)
- `broadcast()` must copy the subscriber set before iterating (`list(...)`) to avoid "set changed size during iteration" if a client disconnects mid-broadcast.
- Sends within a broadcast use `asyncio.gather`, not a sequential loop, so one slow client doesn't delay others.

### Rendering split (frontend, not yet built)
- **ISR** (`revalidate: 60–120s`) for standings/news — staleness is invisible to users here.
- **Client component** (`"use client"`) for the live scoreboard — bypasses ISR entirely, opens its own WebSocket on mount. Initial value comes either from an ISR-cached prop (fast paint, tiny staleness window) or a client-side fetch on mount (always fresh, small loading flash) — not yet decided which.

### Entity resolution across providers (designed, not yet built)
Team/league IDs differ per provider. Planned solution: a `team_id_mappings` table (`canonical_team_id, source, source_team_id`) — this table exists in earlier model drafts but was written before the bzzoiro pivot; **needs to be revisited** since current code has no cross-provider ID reconciliation yet.

**League config pattern (designed, partially implemented via developer's own dataframe export from bzzoiro):**
- Stable fields (`id`, `name`, `country`) → hardcode in a static `LEAGUES` dict, keyed by `name_country` (not `name` alone — league names collide across countries).
- Volatile fields (`current_season.id`) → **do not hardcode**, fetch at runtime and cache with periodic refresh, since season IDs roll over.

---

## 5. Config Layer (`config/`)

```
config/
├── __init__.py      # re-exports: from .settings import settings
└── settings.py
```

Uses `pydantic-settings`. Fields are matched to `.env` keys **case-insensitively but not name-insensitively** — `DB_URL` in `.env` will NOT satisfy a `database_url` field; names must match exactly modulo case. This exact mismatch caused multiple debugging sessions during setup (see §10).

Known current fields (verify against actual file — this list was assembled from conversation, not a live read):
```python
class Settings(BaseSettings):
    database_url: str
    redis_url: str
    api_football_key: Optional[str] = None
    bzzorio_api_key: Optional[str] = None
    bzzorio_base_url: Optional[str] = None

    class Config:
        env_file = ".env"
```
Note: project code consistently spells it `bzzorio` (o-r-i-o) even though the actual service domain is `bzzoiro` (o-i-r-o). This is a deliberate, consistent internal spelling choice, not a bug — don't "fix" it without updating every reference.

`.env` (values illustrative, not the real secrets):
```
DATABASE_URL=postgresql+asyncpg://mezzala:mezzala_2345@localhost:5432/mezzala_db
REDIS_URL=redis://localhost:6379
POSTGRES_USER=mezzala
POSTGRES_PASSWORD=mezzala_2345
POSTGRES_DB=mezzala_db
BZZORIO_API_KEY=<key>
BZZORIO_BASE_URL=https://sports.bzzoiro.com/
API_FOOTBALL_KEY=<optional, not currently used>
```

**`.env` must never be committed.** `.env.example` (same keys, blank values) should exist for onboarding and IS safe to commit. Verify `git log --all --full-history -- .env` is clean — if `.env` was ever committed, rotate all keys rather than trying to scrub history.

---

## 6. Database Layer (`database/`)

```
database/
├── __init__.py
├── database.py       # engine, async_session factory, get_db() dependency
├── models.py          # SQLAlchemy ORM models
├── repository.py       # ALL reads/writes go through here — no raw queries elsewhere
└── migrations/
    ├── env.py
    └── versions/
```

### `database.py`
- `create_async_engine(settings.database_url, echo=False, pool_size=10, max_overflow=5)`
- `async_sessionmaker(engine, expire_on_commit=False)` — `expire_on_commit=False` is deliberate: without it, objects become unusable immediately after commit, forcing redundant re-queries (matters for the poller, which writes then immediately may need the same object).
- `get_db()` is an async generator used as a FastAPI dependency (`Depends(get_db)`). Session opens before `yield`, closes automatically after, via `async with`.
- **The poller does NOT use `get_db()`** — it's not a request/response cycle. It calls `async_session()` directly, scoped per write.

### `models.py` — Schema evolution (important history)
The schema went through real iteration — an agent picking this up should know the *current* state, not the history, but the reasoning matters for future changes:

1. Started as two tables: `Match` (general) + a separate `LiveFixture` table for live-specific fields.
2. **Consolidated into a single `Fixture` table** with nullable columns, because a match's data genuinely changes shape over its lifecycle (scheduled → live → finished), and splitting it across tables caused "which table is the source of truth" ambiguity.

**Current consolidated schema:**
```python
class Fixture(Base):
    __tablename__ = "fixtures"

    match_id: Mapped[int] = mapped_column(primary_key=True)
    league_id: Mapped[int] = mapped_column(Integer, index=True)
    home_team_id: Mapped[int] = mapped_column(Integer)
    home_team: Mapped[str] = mapped_column(String)
    away_team_id: Mapped[int] = mapped_column(Integer)
    away_team: Mapped[str] = mapped_column(String)
    venue_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    event_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))  # MUST be timezone=True — see §10 bug
    status: Mapped[str] = mapped_column(String, index=True, default="scheduled")

    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_minute: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_score_ht: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score_ht: Mapped[int | None] = mapped_column(Integer, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),   # MUST be a lambda, not a called value — see §10 bug
        onupdate=lambda: datetime.now(timezone.utc),
    )
```

**Open item flagged but not yet resolved:** `status` needs to be populated from an explicit field in the bzzoiro response, not inferred from other fields being null/non-null (inferring breaks once "finished" also has null `current_minute`). Check whether bzzoiro's raw payload includes a status field and map it directly in `transform_fixture`.

**`TeamIDMapping`** table was designed earlier for cross-provider entity resolution but predates the bzzoiro-only pivot — needs review, may not reflect current provider set.

### `repository.py` — the abstraction layer
Every DB read/write in the entire app goes through functions here — no other file should contain a raw `select()`/`insert()`.

```python
async def upsert_fixture(db: AsyncSession, fixture_data: dict) -> Fixture:
    stmt = insert(Fixture).values(**fixture_data)
    stmt = stmt.on_conflict_do_update(
        index_elements=["match_id"],
        set_={k: v for k, v in fixture_data.items() if k != "match_id"},
    )
    await db.execute(stmt)
    await db.commit()
    result = await db.execute(select(Fixture).where(Fixture.match_id == fixture_data["match_id"]))
    return result.scalar_one()
```

`orm_to_dict()` also lives here — converts an ORM instance back to a plain dict (needed since ORM objects have no `.model_dump()`; that's Pydantic-only):
```python
def orm_to_dict(obj) -> dict:
    return {col.key: getattr(obj, col.key) for col in inspect(obj).mapper.column_attrs}
```

**Naming convention enforced project-wide, due to a real bug encountered (§10):** Pydantic schemas (raw-fetch return types) and SQLAlchemy ORM models must NOT share identical class names in files where both are imported — caused a silent wrong-binding bug previously (`LiveFixture` existed as both a Pydantic schema and an ORM model simultaneously). Current convention: ORM models live in `database/models.py` under their plain name (`Fixture`); Pydantic fetch-schemas should be named distinctly (e.g. `FixtureData`) if both are ever imported into the same file.

**Type-flow rule to keep straight when writing new code:** `.model_dump()` is Pydantic-only — call it right after a `fetch_*` function returns, before passing into any `upsert_*`. Anything returned FROM `upsert_*` or a `select()` is an ORM object — use `orm_to_dict()`, never `.model_dump()`, on those.

### Migrations (Alembic)
- Installed and invoked as `python -m alembic ...` (not bare `alembic`) — Windows PATH issue, module invocation sidesteps it reliably.
- `database/migrations/env.py` must set the sync-driver URL explicitly (Alembic runs synchronously, app uses `asyncpg`):
  ```python
  config.set_main_option("sqlalchemy.url", settings.database_url.replace("+asyncpg", ""))
  target_metadata = Base.metadata
  ```
  This line must execute at module top-level, before `run_migrations_online`/`offline` are defined/called.
- Requires `psycopg2-binary` installed separately from the app's `asyncpg` driver — two different drivers for two different execution modes (sync migrations vs. async app).
- Workflow for any schema change: `python -m alembic revision --autogenerate -m "description"` → **inspect the generated file before applying** (autogenerate isn't infallible) → `python -m alembic upgrade head`.
- If autogenerate produces an empty migration, the new model class likely isn't imported anywhere `env.py`'s module tree touches — it never registered on `Base.metadata`.
- All commands must run from `project_root`, not from inside `database/` — relative imports in `env.py` (`from config import settings`) fail otherwise since Python adds CWD to the import path.

---

## 7. Docker / Local Infra

`docker-compose.yml` (project root) — Postgres + Redis, both with named volumes (survive restarts) and healthchecks:

```yaml
services:
  postgres:
    image: postgres:16-alpine
    container_name: mezzala_postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports: ["5432:5432"]
    volumes: [postgres_data:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]

  redis:
    image: redis:7-alpine
    container_name: mezzala_redis
    ports: ["6379:6379"]
    volumes: [redis_data:/data]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]

volumes:
  postgres_data:
  redis_data:
```

**Critical constraint:** `.env` must sit in the same directory Docker Compose is invoked from (normally project root, next to `docker-compose.yml`) — Compose silently defaults every referenced variable to blank if it can't find the file, with no hard error (see §10 for the exact failure mode this caused).

**Also critical:** Postgres env vars (`POSTGRES_USER`/`PASSWORD`/`DB`) only take effect on **first initialization** of the data volume. Changing `.env` after the fact requires `docker compose down -v` (destroys the volume) + `up -d` again to actually take effect — a plain restart will not pick up new credentials.

---

## 8. Poller (`poller/poller.py`)

Standalone script, run as its own process — never inside FastAPI, never replicated.

### Responsibilities, per cycle:
1. Fetch raw data from bzzoiro (live fixtures every ~15s — see §10 for why 5s was too aggressive; standings every 30min; stat leaders every 6hr; upcoming fixtures every 24hr).
2. Normalize via `transform_fixture()` (unified function, takes a `status` param — see §6 schema note).
3. UPSERT to Postgres via `upsert_fixture()` — **always**, every cycle, regardless of whether anything changed.
4. Diff-check against in-memory last-known-state (see §9) — publish to Redis **only if changed**.
5. RSS ingestion runs on its own separate, much slower schedule (15–30 min) — must not block or be blocked by the live-score loop.

### Scheduling — APScheduler
```python
scheduler = AsyncIOScheduler()
scheduler.add_job(poll_live_fixtures, "interval", seconds=15, id="live_fixtures")
scheduler.add_job(poll_standings, "interval", minutes=30, id="standings")
scheduler.add_job(poll_stats, "interval", hours=6, id="stats")
scheduler.add_job(poll_upcoming_fixtures, "interval", hours=24, id="fixtures")
scheduler.start()
```
Process must be kept alive after `scheduler.start()` (which returns immediately) via `await asyncio.Event().wait()` inside an `async def main()` — otherwise the process exits immediately and no job ever fires. This was an actual bug hit during setup.

### Fetching — concurrency requirement
Per-league fetches inside a single poll cycle must run **concurrently** via `asyncio.gather(..., return_exceptions=True)`, not sequentially — sequential fetching across several leagues caused cycle time to exceed the poll interval itself, triggering APScheduler's `max_instances=1` skip-if-still-running behavior (see §10).

### Provider abstraction
`fetch_*` functions are bzzoiro-specific today (`fetch_live_fixtures`, `fetch_league_fixtures`, `fetch_fixture`, `fetch_standings`, `fetch_stat`) — each hits `{bzzorio_base_url}/...` with `Authorization: Token {bzzorio_api_key}`. If/when API-Football or another provider is reintroduced, the established pattern (per this project's own architecture docs) is: keep the internal `Fixture`/normalized shape identical, add a second `transform_*_apifootball()` function, and only the fetch/transform layer should know which provider it's talking to.

### Redis caching (for non-live, cacheable data)
Standings and stat leaders are cached in Redis with TTLs matching their own refresh interval (not published via pub/sub — this is plain caching, a different Redis use than the live-score pub/sub):
```python
await cache_set(f"standings:{league_id}", standings, ttl_seconds=1800)
await cache_set(f"stats:{league_id}:{stat}", stats, ttl_seconds=21600)
```
Values must be JSON-serialized before storage (`json.dumps(..., default=str)` for plain dicts, or `.model_dump(mode="json")` for Pydantic objects) — Redis has no concept of Python objects, everything is bytes/strings. `pickle` was explicitly ruled out as unsafe for this (arbitrary code execution risk on deserialization from shared infra).

---

## 9. Change Detection (diff-before-publish)

**Decision made and reasoning, in case this needs to be revisited:** state comparison happens via a **module-level in-memory dict inside the poller process**, not Redis and not a Postgres pre-read.

- **Why not query Postgres first?** Doubles DB traffic every cycle for no benefit, since the write is about to happen anyway.
- **Why not Redis?** A network round-trip to compare state that the *same process* already computed seconds ago has no upside — Redis is for state that must be shared *across processes* or survive a restart in a way that matters; neither applies here.
- **Why in-memory is safe despite not being persistent:** the poller is a singleton, so it's always the same process reading and writing this state. On restart, the dict resets to empty, causing one harmless over-publish burst (every live match looks "new," gets published once) — Postgres is unaffected (always written regardless), and WebSocket clients just get one redundant no-op update.

```python
_last_known_state: dict[int, tuple] = {}

def has_changed(match_id: int, fixture_data: dict) -> bool:
    snapshot = (
        fixture_data["status"],
        fixture_data["home_score"],
        fixture_data["away_score"],
        fixture_data["current_minute"],
    )
    if _last_known_state.get(match_id) == snapshot:
        return False
    _last_known_state[match_id] = snapshot
    return True
```
Only fields that can actually change mid-match belong in the comparison tuple — static fields (team names, venue) would just cause wasted comparisons.

**This is implemented conceptually but not yet confirmed wired into `poller.py`** — verify current state of the file; this was the most recent topic discussed before this document was requested.

---

## 10. Bugs Already Hit and Fixed (don't reintroduce these)

| Bug | Cause | Fix |
|---|---|---|
| `Settings()` `ValidationError: field required` | `.env` key name didn't exactly match the Pydantic field name (e.g. `DB_URL` vs `database_url`, `BZZORIO_API_KEY` missing entirely) | Pydantic-settings matches names case-insensitively but NOT if the name itself differs. Always verify exact match. |
| Docker Compose vars "defaulting to blank string" | `.env` not found relative to where `docker compose` was invoked, or `.env` key name (`POSTGRES_PASS`) didn't match what `docker-compose.yml` referenced (`${POSTGRES_PASSWORD}`) | Ensure `.env` sits next to `docker-compose.yml`; keep key names identical between both files. |
| `alembic: command not found` (Windows) | `pip`-installed console scripts not on PATH | Use `python -m alembic ...` instead of bare `alembic`. |
| Alembic `ArgumentError: Could not parse SQLAlchemy URL` | `config.set_main_option(...)` either missing from `env.py` or placed after the functions that need it | Must be set at module top-level in `env.py`, before `run_migrations_online`/`offline` definitions. |
| Alembic `ModuleNotFoundError: psycopg2` | Alembic runs sync migrations; app uses async `asyncpg` driver only | Install `psycopg2-binary` as a separate dependency purely for migrations. |
| `ConnectionRefusedError` on `localhost:5432` | Postgres container not running / port conflict with a native Windows Postgres install | Check `docker compose ps`; check `netstat -ano \| findstr :5432` for a port collision. |
| `can't subtract offset-naive and offset-aware datetimes` (asyncpg) | Column defined as `DateTime` (naive) while normalize function produced a tz-aware `datetime` (via `.fromisoformat()` on a `Z`-suffixed ISO string) | Column must be `DateTime(timezone=True)` to match the tz-aware Python values actually being sent. Required a new Alembic migration. |
| `default=datetime.now(timezone.utc)` silently frozen at class-definition time | Called the function immediately instead of passing a callable | Must be `default=lambda: datetime.now(timezone.utc)`. |
| `'LiveFixture' object has no attribute 'model_dump'` | Called Pydantic's `.model_dump()` on an object that was actually the SQLAlchemy ORM return value from `upsert_*` | Use `orm_to_dict()` (custom helper) for anything returned by `upsert_*`/`select()`; `.model_dump()` only ever applies to the Pydantic object immediately after a `fetch_*` call. |
| Silent wrong-binding risk from duplicate class names | A Pydantic schema and a SQLAlchemy ORM model were both named `LiveFixture` and both imported into the same file | Never give a Pydantic fetch-schema and an ORM model the same class name if both might be imported together. |
| APScheduler: "maximum number of running instances reached (1)" | `poll_live_fixtures` (5s interval) took longer than 5s per run because per-league fetches ran sequentially | Fetch leagues concurrently via `asyncio.gather(return_exceptions=True)`; also bumped interval toward the provider's actual refresh cadence (~15s) since sub-15s polling returns mostly-identical data anyway. |
| Poller process exiting immediately after `scheduler.start()` | `scheduler.start()` is non-blocking; nothing kept the event loop alive afterward | Wrap in `async def main()` ending with `await asyncio.Event().wait()`, run via `asyncio.run(main())`. |
| Feedparser missing BBC's `<media:thumbnail>` despite `bozo=False` (feed parsed cleanly) | `feedparser`'s namespace handling didn't surface this tag for this specific feed, for reasons not fully diagnosed | Fell back to `xml.etree.ElementTree` with explicit namespace dict (`{"media": "http://search.yahoo.com/mrss/"}`) matched to the feed's actual declared URI — confirmed working. |
| `fetch_stat` returning `None` always | Function body had `print(stats)` instead of `return stats` | One-line fix — flagged, not yet confirmed corrected in the actual file. |

---

## 11. Implementation Status (as of this document)

**Built and confirmed working:**
- `.env` / `config/settings.py` resolving correctly.
- Docker Compose (Postgres + Redis) running with healthchecks.
- Alembic migrations applying cleanly; `fixtures` table exists (consolidated schema).
- `database/database.py`, `database/repository.py` (`upsert_fixture`, `orm_to_dict`) in place.
- Poller: bzzoiro fetch functions for live fixtures (confirmed working — real match data observed flowing through, e.g. "Everton 0-1 Manchester United"), upcoming fixtures, standings, stat leaders.
- APScheduler wired with all four job intervals; process-keep-alive pattern in place.
- Concurrent per-league fetching via `asyncio.gather`.
- Fixture consolidation (single table, nullable live-fields) — schema decided, migration approach discussed, **verify it's actually been applied**.

**Designed but not yet implemented:**
- Redis publish-on-change wiring in the poller (§9 — logic designed, needs confirmation it's in the actual file).
- `status` field population from an explicit provider field (currently a gap — nothing sets it yet).
- FastAPI app itself: no REST routes, no WebSocket hub, no `ConnectionManager`, no `lifespan`/`redis_listener` startup task exist yet as actual code — all designed in conversation only.
- RSS ingestion pipeline: `NewsItem` schema, `FEEDS` registry, `IMAGE_EXTRACTORS` registry pattern — all designed with working BBC extraction logic confirmed, but not yet assembled into a running ingestion loop or wired to Postgres.
- League config (`LEAGUES` dict with stable IDs) — developer has a working dataframe pulled from bzzoiro; needs to be turned into the actual static config file (`leagues.py`).
- `TeamIDMapping` table / cross-provider entity resolution — designed pre-bzzoiro-pivot, needs revisiting since bzzoiro is currently the sole active source (no cross-provider merging happening yet in practice).
- Next.js frontend — not started at all; fully designed only (ISR split, WebSocket client component, initial-state handling).
- Deployment (Railway/Fly.io/Vercel), CI/CD (GitHub Actions), testing (pytest), monitoring (Sentry) — none started.
- `.env.example`, finalized `.gitignore` — content specified in conversation, verify actually created in repo.
- Historical seed import from openfootball — not started.
- TheSportsDB integration for crests — not started.

---

## 12. Immediate Next Steps (in dependency order)

1. Confirm `status` field is populated correctly from bzzoiro's raw response in `transform_fixture`.
2. Confirm Redis publish-on-change (§9) is actually wired into `poll_live_fixtures`, not just designed.
3. Build the FastAPI app: `lifespan` startup task (`redis_listener`), `ConnectionManager` (inverted-index design, §4), `/ws/live` endpoint, `/matches` REST endpoint using `repository.py` functions.
4. Build `leagues.py` from the developer's bzzoiro dataframe (stable fields only; season ID resolved at runtime, not hardcoded).
5. Finish RSS ingestion loop end-to-end (fetch → normalize → dedupe per-source image extractors → Postgres) and add it as its own APScheduler job.
6. Scaffold the Next.js frontend against the now-real REST/WS endpoints.
7. Revisit cross-provider entity resolution once/if a second live-data provider is reintroduced.

---

*This document should be updated as the project progresses — it reflects a snapshot of decisions and status, not a static spec.*
