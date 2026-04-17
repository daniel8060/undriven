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
| `gmaps.py` | Google Maps API calls (autocomplete, geocode, driving_miles) |
| `config.py` | Env-var loading; CARS, GEOCODE_FOCUS, CO2_KG_PER_GALLON |
| `frontend/src/` | React SPA source (pages, components, context, hooks) |
| `frontend/src/styles/index.css` | All styles; CSS variables (--surface, --accent, etc.) |
| `.claude/agents/` | Project-level Claude agents: deploy.md, test.md |

## Environment variables

Loaded from `.env` at project root (not committed). Required:
- `GOOGLE_MAPS_API_KEY` — hard fail if missing (no fallback)
- `SECRET_KEY` — JWT signing key

Optional:
- `DATABASE_URL` — defaults to `sqlite:///instance/trips.db`

`CARS`, `GEOCODE_FOCUS`, `CO2_KG_PER_GALLON` stay as Python config in `config.py`.

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
- Fresh install: `cd backend && uv run alembic -c migrations/alembic.ini upgrade head`
- **Local db lives at `instance/trips.db`**. To wipe local state: `rm instance/trips.db && cd backend && uv run alembic -c migrations/alembic.ini upgrade head`
- When deploying to Pi where schema already exists: `alembic stamp head` then future upgrades work normally.

## Deployment (Pi — ulmo)

```bash
# Deploy update (or use the 'deploy' Claude agent)
# 1. Build frontend locally
cd frontend && npm run build

# 2. Copy dist to Pi
scp -r frontend/dist/* ulmo:/home/daniel/projects/undriven/frontend/dist/

# 3. Pull code, sync deps, migrate, restart
ssh ulmo "cd /home/daniel/projects/undriven/backend && git -C .. pull && ~/.local/bin/uv sync && ~/.local/bin/uv run alembic -c migrations/alembic.ini upgrade head && sudo systemctl restart undriven"

# Create user
ssh ulmo "cd /home/daniel/projects/undriven/backend && ~/.local/bin/uv run python cli.py create-user <username>"

# Logs
ssh ulmo "journalctl -u undriven -f"
```

- No Node.js on Pi — React is built locally, `dist/` deployed via scp
- nginx: `/api/` proxied to uvicorn:8000, everything else served from `frontend/dist/` with `try_files $uri /index.html`
- systemd unit: uvicorn (`uvicorn backend.main:app --host 127.0.0.1 --port 8000`)
- `uv` lives at `~/.local/bin/uv` on the Pi
- nginx config: `/etc/nginx/sites-available/undriven`
- App path: `/home/daniel/projects/undriven`
- mDNS: `http://undriven.local`

## Running locally

```bash
# Backend
cd backend && uv run uvicorn backend.main:app --reload --port 8000  # API on :8000

# Frontend (separate terminal)
cd frontend && npm run dev   # Vite dev server on :5173, proxies /api → :8000

# Tests
cd backend && uv run pytest -v  # 44 tests

# Migrations
cd backend && uv run alembic -c migrations/alembic.ini upgrade head
```

## Auth

- JWT in httpOnly cookie (`access_token`), SameSite=Lax, 30-day expiry
- `GET /api/me` — check auth state; `POST /api/login`, `/api/signup`, `/api/logout`
- All `/api/*` routes require auth via `get_current_user` dependency
- Users created via CLI: `python backend/cli.py create-user <username>`, or via `/signup`

## Trip Segments

- A trip can have 0+ segments (multi-mode trips: bike to station, train downtown, etc.)
- `trip_segments` table: trip_id, position, start_loc, end_loc, mode, miles
- Parent trip stores summary: start=first seg, end=last seg, mode=first seg's mode, miles=sum
- 0 segments = flat display in trip history; has segments = expandable detail row
