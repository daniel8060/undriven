---
name: deploy
description: Deploy the Undriven app to the Raspberry Pi (ulmo). Use this after a PR is merged to main.
tools: Bash
---

Deploy the Undriven FastAPI + React app to the Raspberry Pi (ulmo, 10.0.0.80).

## Steps

Run each step sequentially and report its output:

1. Build the React frontend locally:
   cd /Users/danielbecerra/projects/undriven/frontend && npm run build

2. Deploy the frontend dist to the Pi:
   scp -r /Users/danielbecerra/projects/undriven/frontend/dist/* ulmo:/home/daniel/projects/undriven/frontend/dist/

3. Pull latest code, sync backend deps, run migrations, and restart:
   ssh ulmo "cd /home/daniel/projects/undriven/backend && git -C .. pull && ~/.local/bin/uv sync && ~/.local/bin/uv run alembic -c migrations/alembic.ini upgrade head && sudo systemctl restart undriven"

4. Verify the service came back up:
   ssh ulmo "systemctl is-active undriven"

Report what each step outputs. If any step fails, show the full error output and stop.

## Notes

- If alembic fails on a fresh Pi where the schema pre-exists (no `alembic_version` table yet), run `alembic stamp head` once, then future `upgrade head` runs work normally.

- No Node.js on Pi — React is built locally, `dist/` deployed via scp
- nginx: `/api/` proxied to uvicorn:8000, everything else served from `frontend/dist/` with `try_files $uri /index.html`
- systemd unit: uvicorn (`uvicorn backend.main:app --host 127.0.0.1 --port 8000`)
- `uv` lives at `~/.local/bin/uv` on the Pi
- nginx config: `/etc/nginx/sites-available/undriven`
- App path: `/home/daniel/projects/undriven`
- mDNS: `http://undriven.local`
