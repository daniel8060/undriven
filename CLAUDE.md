# Undriven — Claude Context

Personal Flask app for tracking car miles replaced by non-car trips (bike, walk, train, etc.).
Runs on a Raspberry Pi (ulmo, 10.0.0.80) behind nginx + gunicorn.

## Stack

- **Flask 3.0** — `create_app()` factory in `app.py`
- **SQLAlchemy 2.0** via Flask-SQLAlchemy; models in `models.py`
- **Flask-Migrate / Alembic** — all schema changes go through migrations, never `db.create_all()` in production
- **Flask-Login + bcrypt** — single-user auth; user created via `flask create-user <username>`
- **Google Maps Platform** — Places API (New) + Routes API + Geocoding API (see `gmaps.py`)
- **uv** for dependency management (`pyproject.toml`)
- **pytest** test suite in `tests/`

## Key files

| File | Purpose |
|---|---|
| `app.py` | App factory, all routes, CLI commands |
| `models.py` | SQLAlchemy models: User, Trip, SavedAddress, SavedCar |
| `db.py` | Query helpers (get_summary, get_all_trips, etc.) |
| `gmaps.py` | Google Maps API calls (autocomplete, geocode, driving_miles) |
| `sync.py` | log_trip() — orchestrates geocoding + DB insert |
| `config.py` | Env-var loading; CARS and GEOCODE_FOCUS as Python dicts |
| `static/css/style.css` | All styles; uses CSS variables (--surface, --accent, etc.) |
| `static/js/` | form.js, autocomplete.js, chart.js |
| `templates/` | Jinja2 templates; static assets use `?v={{ rev }}` cache-busting |

## Environment variables

Loaded from `.env` at project root (not committed). Required:
- `GOOGLE_MAPS_API_KEY` — hard fail if missing (no fallback)
- `SECRET_KEY` — Flask session key

Optional:
- `DATABASE_URL` — defaults to `sqlite:///trips.db`
- `SHEET_ID`, `SHEET_TAB`, `GOOGLE_CREDENTIALS_FILE` — Google Sheets sync

`CARS`, `GEOCODE_FOCUS`, `CO2_KG_PER_GALLON` stay as Python config in `config.py`.

## Google Maps API notes

Both autocomplete and routing use new endpoints — do not use legacy Google APIs:
- **Autocomplete**: `POST places.googleapis.com/v1/places:autocomplete` with `X-Goog-Api-Key` header
- **Routing**: `POST routes.googleapis.com/directions/v2:computeRoutes` with `X-Goog-Api-Key` + `X-Goog-FieldMask` headers
- **Geocoding**: `GET maps.googleapis.com/maps/api/geocode/json` with `key` param

HTTP errors from Google should be caught and re-raised as `MapsError` (not `raise_for_status()`).

## Database / migrations

- Schema is managed entirely by Alembic. Never add `db.create_all()` to `create_app()`.
- Test fixtures call `db.create_all()` explicitly — that is intentional and fine.
- Fresh install: `flask db upgrade` runs `0001_initial_schema` and creates all tables cleanly.
- **Local db lives at `instance/trips.db`** — Flask resolves relative SQLite URIs to the instance folder. To wipe local state: `rm instance/trips.db && flask db upgrade`.
- When a migration gets stamped without running: `flask db stamp <prev_revision>` then `flask db upgrade`.
- When squashing migrations: existing deployments need `flask db stamp head` since their schema is already correct.

## Deployment (Pi — ulmo)

```bash
# Deploy update
ssh ulmo "cd /home/daniel/projects/undriven && git pull && ~/.local/bin/uv sync && ~/.local/bin/uv run flask db upgrade && sudo systemctl restart undriven"

# Create user
ssh ulmo "cd /home/daniel/projects/undriven && ~/.local/bin/uv run flask create-user <username>"

# Logs
ssh ulmo "journalctl -u undriven -f"
# or: /var/log/undriven/access.log, /var/log/undriven/error.log
```

- `uv` lives at `~/.local/bin/uv` on the Pi (not in PATH by default for ssh commands)
- nginx config: `/etc/nginx/sites-available/undriven`
- App path: `/home/daniel/projects/undriven`
- mDNS: `http://undriven.local`

## Running locally

```bash
uv run flask run        # dev server
uv run pytest -v        # test suite (39 tests)
uv run flask db upgrade # apply pending migrations
```

## Auth

- All routes require login (`@login_required`)
- Login: `GET/POST /login`; signup: `GET/POST /signup`; logout: `POST /logout`
- Users can also be created via CLI: `flask create-user <username>`

## Planned phases (not yet built)

- **Phase 4 — Saved Addresses**: per-user address shortcuts; chip UI in log form; From/To mutual exclusion
