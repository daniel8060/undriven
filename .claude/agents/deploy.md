---
name: deploy
description: Deploy the Undriven app to the Raspberry Pi (ulmo). Use this after a PR is merged to main.
tools: Bash
---

Deploy the Undriven Flask app to the Raspberry Pi (ulmo, 10.0.0.80).

Run each step sequentially and report its output:

1. Pull latest code and sync dependencies:
   ssh ulmo "cd /home/daniel/projects/undriven && git pull && ~/.local/bin/uv sync && ~/.local/bin/uv run flask db upgrade && sudo systemctl restart undriven"

2. Verify the service came back up:
   ssh ulmo "systemctl is-active undriven"

Report what each step outputs. If any step fails, show the full error output and stop.
