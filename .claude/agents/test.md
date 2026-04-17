---
name: test
description: Run the Undriven pytest suite and report results. Use after making code changes.
tools: Bash
---

Run the full test suite for the Undriven backend:

  cd /Users/danielbecerra/projects/undriven/backend && uv run pytest -v 2>&1

Report the full output. If any tests fail, clearly identify which ones and what the failure message says.
