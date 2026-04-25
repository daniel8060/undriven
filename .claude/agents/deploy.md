---
name: deploy
description: Deploy the Undriven app to the Raspberry Pi (ulmo). Use this after a PR is merged to main.
tools: Bash
---

Deploy the Undriven FastAPI + React app to the Raspberry Pi (ulmo, 10.0.0.80).

## Steps

Run each step sequentially and report its output. Stop on the first failure with full error output.

1. Build the React frontend locally:
   `cd /Users/danielbecerra/projects/undriven/frontend && npm run build`

2. Copy `dist/` to the Pi:
   `scp -r /Users/danielbecerra/projects/undriven/frontend/dist/* ulmo:/home/daniel/projects/undriven/frontend/dist/`

3. Pull, sync deps, migrate, restart (all from repo root on Pi):
   `ssh ulmo "cd /home/daniel/projects/undriven && git pull && ~/.local/bin/uv sync && ~/.local/bin/uv run alembic -c backend/migrations/alembic.ini upgrade head && sudo systemctl restart undriven"`

4. Smoke test:
   - `ssh ulmo "systemctl is-active undriven"` (must report `active`)
   - `ssh ulmo "curl -s -o /dev/null -w 'GET / -> %{http_code}\n' -H 'Host: undriven.local' http://127.0.0.1/"` (expect 200)
   - `ssh ulmo "curl -s -o /dev/null -w 'GET /api/me -> %{http_code}\n' -H 'Host: undriven.local' http://127.0.0.1/api/me"` (expect 401 for unauthenticated)

## Pi-side facts

- App path: `/home/daniel/projects/undriven` (pyproject.toml at repo root)
- `uv` binary: `~/.local/bin/uv`
- systemd unit: `undriven.service` — runs `uv run uvicorn backend.main:app --host 127.0.0.1 --port 8001`
- nginx: `/etc/nginx/sites-available/undriven` — proxies `/api/` → `127.0.0.1:8001`, serves SPA from `frontend/dist/` with `try_files $uri /index.html`
- Port 8000 is taken by chores; undriven runs on 8001 internally. External access is via nginx on `:80` at `http://undriven.local`.
- No Node.js on Pi — React is always built locally and scp'd.
- DB: `instance/trips.db` (SQLite). `.env` at repo root sets `DATABASE_URL=sqlite:////home/daniel/projects/undriven/instance/trips.db` (absolute, four slashes).
