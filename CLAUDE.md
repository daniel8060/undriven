# Undriven — Claude Context

Personal app for tracking car miles replaced by non-car trips (bike, walk, train, etc.).
Runs on a Raspberry Pi (ulmo, 10.0.0.80) behind nginx + uvicorn.

## Stack

- **FastAPI** — backend API in `backend/main.py`
- **React 19 + Vite + TypeScript** — SPA frontend in `frontend/`
- **SQLAlchemy 2.0** (plain declarative base); models in `backend/models.py`
- **Alembic** (standalone) — all schema changes go through migrations
- **JWT auth** in httpOnly cookies (python-jose + bcrypt)
- **Google Maps Platform** — Places API (New) + Routes API + Geocoding API (see `gmaps.py`)
- **uv** for backend dependency management (`backend/pyproject.toml`)
- **npm** for frontend (`frontend/package.json`)
- **pytest** test suite in `backend/tests/` (44 tests)

## Key files

| File | Purpose |
|---|---|
| `backend/main.py` | FastAPI app, CORS, router includes |
| `backend/models.py` | SQLAlchemy models: User, Trip, TripSegment, SavedAddress, SavedCar |
| `backend/database.py` | Engine, SessionLocal, `get_db()` dependency |
| `backend/auth.py` | JWT create/decode, `get_current_user` dependency, password hashing |
| `backend/schemas.py` | Pydantic request/response models |
| `backend/db.py` | Query helpers (get_summary, get_all_trips, insert_trip, etc.) |
| `backend/sync.py` | log_trip() — orchestrates routing + DB insert (supports segments) |
| `backend/cli.py` | CLI commands: create-user, seed-cars |
| `backend/routers/` | auth_router, trips, cars, addresses, maps |
| `backend/migrations/` | Standalone Alembic migrations (0001–0003) |
| `backend/tests/` | pytest suite: test_auth, test_db, test_gmaps, test_sync |
| `backend/gmaps.py` | Google Maps API calls (autocomplete, geocode, driving_miles) |
| `backend/config.py` | Env-var loading; CARS, GEOCODE_FOCUS, CO2_KG_PER_GALLON |
| `frontend/src/` | React SPA source (pages, components, context, hooks) |
| `frontend/src/styles/index.css` | All styles; CSS variables (--surface, --accent, etc.) |
| `.claude/agents/` | Project-level Claude agents: deploy.md, test.md |
| `~/.claude/agents/ulmo.md` | System-level agent: sysadmin for ulmo |


## Google Maps API notes

Do not use legacy Google APIs:
- **Autocomplete**: `POST places.googleapis.com/v1/places:autocomplete` with `X-Goog-Api-Key` header
- **Routing**: `POST routes.googleapis.com/directions/v2:computeRoutes` with `X-Goog-Api-Key` + `X-Goog-FieldMask` headers
- **Geocoding**: `GET maps.googleapis.com/maps/api/geocode/json` with `key` param

HTTP errors from Google should be caught and re-raised as `MapsError` (not `raise_for_status()`).

## Database / migrations

- Schema is managed entirely by Alembic (standalone). Never add `Base.metadata.create_all()` in production.
- Test fixtures call `Base.metadata.create_all()` explicitly — that is intentional and fine.
- Migration chain: `0001_initial_schema` → `0002_add_sort_order_to_saved_cars` → `0003_add_trip_segments`
- Fresh install: `uv run alembic -c backend/migrations/alembic.ini upgrade head`
- **Local db lives at `instance/trips.db`**. To wipe local state: `rm instance/trips.db && uv run alembic -c backend/migrations/alembic.ini upgrade head`

## Deployment (Pi — ulmo)

- have the deploy agent handle it


## Agent Coordination

- ALWAYS update agent .md files if relevant changes are made. eg deployment flow change -> update `.claude/agents/deploy.md`
- For sysadmin tasks on ulmo, use the `ulmo` agent and keep `~/.claude/agents/ulmo.md` updated when Pi-side details change.

## Trip Segments

- A trip can have 0+ segments (multi-mode trips: bike to station, train downtown, etc.)
- `trip_segments` table: trip_id, position, start_loc, end_loc, mode, miles
- Parent trip stores summary: start=first seg, end=last seg, mode=first seg's mode, miles=sum
- 0 segments = flat display in trip history; has segments = expandable detail row
