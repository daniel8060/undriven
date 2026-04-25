---
name: deploy
description: Deploy the Undriven app to the Raspberry Pi (ulmo). Use this after a PR is merged to main.
tools: Bash
---

Deploy the Undriven FastAPI + React app to the Raspberry Pi (ulmo, 10.0.0.80).

Node.js is installed on the Pi, so the frontend builds on the Pi — no local build / scp dance.

## Steps

Run each step sequentially and report its output. Stop on the first failure with full error output.

1. Pull, install deps, build frontend, migrate, restart (all on the Pi):
   `ssh ulmo "cd /home/daniel/projects/undriven && git pull && ~/.local/bin/uv sync && cd frontend && npm ci && npm run build && cd .. && ~/.local/bin/uv run alembic -c backend/migrations/alembic.ini upgrade head && sudo systemctl restart undriven"`

2. Smoke test:
   - `ssh ulmo "systemctl is-active undriven"` (must report `active`)
   - `ssh ulmo "curl -s -o /dev/null -w 'GET / -> %{http_code}\n' -H 'Host: undriven.local' http://127.0.0.1/"` (expect 200)
   - `ssh ulmo "curl -s -o /dev/null -w 'GET /api/me -> %{http_code}\n' -H 'Host: undriven.local' http://127.0.0.1/api/me"` (expect 401 for unauthenticated)

## Pi-side facts

- App path: `/home/daniel/projects/undriven` (pyproject.toml at repo root)
- `uv` binary: `~/.local/bin/uv`
- Node.js: `/usr/bin/node` (v24+), npm available
- systemd unit: `undriven.service` — runs `uv run uvicorn backend.main:app --host 127.0.0.1 --port 8001`
- nginx: `/etc/nginx/sites-available/undriven` — proxies `/api/` → `127.0.0.1:8001`, serves SPA from `frontend/dist/` with `try_files $uri /index.html`
- Port 8000 is taken by chores; undriven runs on 8001 internally. External access is via nginx on `:80` at `http://undriven.local`.
- DB: `instance/trips.db` (SQLite). `.env` at repo root sets `DATABASE_URL=sqlite:////home/daniel/projects/undriven/instance/trips.db` (absolute, four slashes).
