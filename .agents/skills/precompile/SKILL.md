---
name: precompile
description: >-
  Precompile Xeelo site settings via GraphQL (Mutate_admin_precompile) and wait
  until GraphQL is healthy. Use when the user asks to precompile, compile
  settings without an Object Transfer, or invokes /precompile.
disable-model-invocation: true
---

# Precompile settings

Call GraphQL `Mutate_admin_precompile` and wait until the GraphQL process is healthy again. Read [AGENT.md](../../AGENT.md) for the full development loop.

Use this when the site already has the Object Transfer applied (or no OT is needed) and you only need to rebuild settings cache / GraphQL schema.

Do **not** auto-run `/precompile` from the change loop. After generate, the loop dry-runs the transfer, then `/publish` (transfer + precompile) per conventions (`ask` or `auto`). Follow this skill only when the user explicitly wants precompile alone.

## Prerequisites

- `projects/<project>/.xeelo-connection.json` exists and is filled in:
  - `xeeloUrl`
  - `token` (GraphQL admin token, `isAdmin`)
- If the connection file is missing or `xeeloUrl` / `token` is empty, stop and tell the user to complete it first (see `/new-project` checklist). If the loader rejects the file, tell the user to **replace** it with `{ "xeeloUrl": "...", "token": "..." }`.

## Inputs

Determine from the user message or ask once:

- **`<project>`** — project slug under `projects/` (e.g. `lz`, `ovnet`). Default to the project mentioned in chat or the one whose connection file is open.

## Python environment

From repo root, use `.venv/bin/python` when `.venv/` exists. If dependencies are missing (`httpx`, …), create the venv and install:

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Use `PYTHON=python` only when system Python already has requirements installed.

## Step 1 — Precompile

```bash
$PYTHON scripts/precompile-settings.py \
  --connection projects/<project>/.xeelo-connection.json
```

Optional `--timeout 600` (GraphQL SQL limit is 10 minutes). HTTP 200 from the mutation is not enough if the process then restarts — the script polls `{xeeloUrl}/graphql-api/health` (fallback `query { health }`).

## Output

Report stdout (`Precompile success=True …`).

## On success — suggest next step

If metadata just changed on the site, **ask** whether to `/download-db` to refresh `env/`. Do not run it unless the user says yes.

## Errors

- **Auth / ACCESS_DENIED** — admin GraphQL token required; there is no refresh.
- **success=false** — report mutation messages; do not claim the site is compiled.
- **Timeout** — precompile can take long on a large site; retry with higher `--timeout`.
