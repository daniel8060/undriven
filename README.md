# Undriven

Track car miles replaced by non-car trips — bike, walk, train, bus, etc. Also CO₂ saved versus a chosen car. Personal multi-user app with a Google Maps–powered logging form.

## Stack

- **Backend** — FastAPI + uvicorn, SQLAlchemy 2.0, Alembic, JWT auth in httpOnly cookies (`backend/`)
- **Frontend** — React 19 + Vite + TypeScript SPA (`frontend/`)
- **DB** — SQLite (`instance/trips.db`)
- **Maps** — Google Maps Platform: Places API (New) + Routes API + Geocoding API
- **Deploy** — Raspberry Pi behind nginx; uvicorn on `:8001`, frontend served as static build from `frontend/dist/`

## Setup

### 1. Install backend deps

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # if you don't have uv
uv sync
```

### 2. Frontend deps

```bash
cd frontend && npm install
```

### 3. `.env` at repo root

```ini
GOOGLE_MAPS_API_KEY=your-key-here
SECRET_KEY=long-random-string-for-jwt-signing
# DATABASE_URL=sqlite:///instance/trips.db   # optional; this is the default
```

`GOOGLE_MAPS_API_KEY` and `SECRET_KEY` are required — the app hard-fails on startup without them. Generate a key in [Google Cloud Console](https://console.cloud.google.com) and enable Places API (New), Routes API, and Geocoding API.

### 4. Initialize the database

```bash
uv run alembic -c backend/migrations/alembic.ini upgrade head
```

### 5. Create a user

```bash
uv run python backend/cli.py create-user <username>
```

(Or use the in-app `/signup` route once the server is running.)

## Running locally

Two terminals:

```bash
# Terminal 1 — API
uv run uvicorn backend.main:app --reload --port 8000

# Terminal 2 — frontend dev server
cd frontend && npm run dev
```

Open [http://localhost:5173](http://localhost:5173). Vite proxies `/api/*` to uvicorn on `:8000`.

## Tests

```bash
uv run pytest -q
```

## Project layout

```
undriven/
├── pyproject.toml
├── uv.lock
├── .env
├── instance/trips.db
├── backend/             # FastAPI package
│   ├── main.py          # app entry + router includes
│   ├── auth.py          # JWT + get_current_user dependency
│   ├── config.py        # CARS, GEOCODE_FOCUS, CO2_KG_PER_GALLON
│   ├── gmaps.py         # Google Maps API wrappers
│   ├── database.py      # engine, SessionLocal, get_db()
│   ├── models.py        # SQLAlchemy models
│   ├── schemas.py       # Pydantic request/response
│   ├── db.py            # query helpers
│   ├── sync.py          # log_trip() — routing + DB insert
│   ├── cli.py           # create-user, seed-cars
│   ├── migrations/      # Alembic
│   ├── routers/         # auth, trips, cars, addresses, maps
│   └── tests/           # pytest suite
└── frontend/            # React 19 + Vite SPA
    ├── package.json
    └── src/
```

## Deployment

The app is deployed on a Raspberry Pi (ulmo). Deploys are driven by the `deploy` Claude agent — see `.claude/agents/deploy.md` for the canonical steps. High level:

1. Build frontend locally (`cd frontend && npm run build`)
2. scp `frontend/dist/` to the Pi
3. `git pull` on the Pi
4. `uv sync` and `alembic upgrade head` on the Pi
5. Restart the `undriven` systemd unit; nginx proxies `/api/` to uvicorn on `:8001` and serves the static frontend
