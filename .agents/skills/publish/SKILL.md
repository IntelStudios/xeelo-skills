---
name: publish
description: >-
  Precompile Xeelo site settings via Admin (PreCompileSettings) and wait for
  the Compile WebSocket event. Use when the user asks to publish, precompile,
  compile settings, or invokes /publish.
disable-model-invocation: true
---

# Publish (Precompile Settings)

Call Admin `PreCompileSettings` and wait until compilation finishes. Read [AGENT.md](../../AGENT.md) for the full development loop.

Typical order after a change: generate OT → ask user → `/push` → ask user → `/publish` → `/download-db`.

Do **not** auto-run `/publish` after generate or `/push`. Only follow this skill when the user explicitly asks to publish or agrees after you asked.

## Prerequisites

- `projects/<project>/.xeelo-connection.json` exists and is filled in:
  - `adminBaseUrl`
  - `siteId` (`XA-SITE-ID`)
  - `credentials` (valid OAuth token JSON)
- If connection file is missing or has empty `siteId` / `credentials`, stop and tell the user to complete it first (see `/new-project` checklist).

## Inputs

Determine from the user message or ask once:

- **`<project>`** — project slug under `projects/` (e.g. `lz`, `ovnet`). Default to the project mentioned in chat or the one whose connection file is open.

## Python environment

From repo root, use `.venv/bin/python` when `.venv/` exists. If dependencies are missing (`httpx`, `websockets`, …), create the venv and install:

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Use `PYTHON=python` only when system Python already has requirements installed.

## Step 1 — Precompile

HTTP 200 with “Compilation started” is **not** done. Connect WebSocket **before** POST, then wait for `Type=Compile` `Status=Success` (or Failed).

```bash
$PYTHON scripts/publish-precompile.py \
  --connection projects/<project>/.xeelo-connection.json
```

Optional flags:

- `--timeout 3600` — seconds to wait for Compile (default 3600)

## Output

Report stdout (`Compile Success: Compilation successful (mm:ss min).`).

## On success — suggest next step

**Ask** whether to `/download-db` to refresh `projects/<project>/env/`. Do not run it unless the user says yes.

## Errors

- **Auth / token expired** — ask user to refresh credentials in `.xeelo-connection.json`.
- **Compile Failed** — report the WS Message/Detail; do not claim the site is published.
- **Timeout** — precompile can take long on a large site; retry with higher `--timeout`.
