---
name: push
description: >-
  Upload a generated Object Transfer ZIP to Xeelo Admin and process it.
  Use when the user asks to push, upload, or deploy an Object Transfer, apply
  a change-loop ZIP on the site, or invokes /push.
disable-model-invocation: true
---

# Push Object Transfer

Upload an Object Transfer ZIP to Xeelo Admin, wait until parse/hierarchy finishes, then process. Read [AGENT.md](../../AGENT.md) for the full development loop.

## Prerequisites

- `projects/<project>/.xeelo-connection.json` exists and is filled in:
  - `adminBaseUrl`
  - `siteId` (`XA-SITE-ID`)
  - `credentials` (valid OAuth token JSON)
- If connection file is missing or has empty `siteId` / `credentials`, stop and tell the user to complete it first (see `/new-project` checklist).

## Inputs

Determine from the user message or ask once:

- **`<project>`** — project slug under `projects/` (e.g. `lz`, `ovnet`). Default to the project mentioned in chat or the one whose connection file is open.
- **ZIP or change loop** — explicit `*-object-transfer.zip`, or `projects/<project>/changes/<slug>/`.

This skill does **not** run `/publish`. After success, **ask** whether to `/publish` — do not run it unless the user says yes.

Do **not** auto-run `/push` after generating a change-loop OT. Only follow this skill when the user explicitly asks to push or agrees after you asked.

## Python environment

From repo root, use `.venv/bin/python` when `.venv/` exists. If dependencies are missing (`httpx`, `pyyaml`, `websockets`, …), create the venv and install:

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Use `PYTHON=python` only when system Python already has requirements installed.

## Step 0 — ZIP must exist

If the user pointed at a change loop and `output/*-object-transfer.zip` is missing, generate first:

```bash
$PYTHON scripts/generate-change-loop.py \
  projects/<project>/changes/<slug>
```

Then continue. Do not invent a ZIP path.

## Step 1 — Push (upload + wait + process)

HTTP 200 from Upload is **not** done. Admin parses XML and builds hierarchy on a background task. The script connects WebSocket **before** POST, blocks until `Type=Task` `Status=Success`, then calls Process, then polls the grid until Completed/Failed.

Change loop (all `output/*-object-transfer.zip`, sequential):

```bash
$PYTHON scripts/push-object-transfer.py \
  --connection projects/<project>/.xeelo-connection.json \
  --loop projects/<project>/changes/<slug>
```

Explicit ZIP:

```bash
$PYTHON scripts/push-object-transfer.py \
  --connection projects/<project>/.xeelo-connection.json \
  --zip projects/<project>/changes/<slug>/output/<object>-object-transfer.zip
```

Optional flags:

- `--timeout 3600` — seconds for parse WS **and** process poll (default 3600)
- `--poll 5` — GridModel poll interval after Process (default 5)
- `--only-test` — test process only; default is real process

Multiple ZIPs in one loop are processed **one after another** (Admin allows only one OT/DB process at a time).

## Output

Report each ZIP from stdout:

- `Processed xmlId=… <filename> status=Completed …`
- Failed process or upload Task Failed → stop; do not continue with remaining ZIPs if the command already exited non-zero

## On success — suggest next step

**Ask** whether to `/publish` (PreCompileSettings). Do not run it unless the user says yes. After publish, ask about `/download-db` to refresh `env/`.

## Errors

- **Auth / token expired** — ask user to refresh credentials in `.xeelo-connection.json`.
- **Upload Task Failed** — incompatible OT version, empty ZIP, or parse error. Do not process.
- **Timeout** — parse or broker process can take long; retry with higher `--timeout`.
- **already ongoing** — another OT/DB transfer is Pending/Processing; wait and retry.
