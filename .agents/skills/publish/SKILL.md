---
name: publish
description: >-
  Upload an Object Transfer JSON via GraphQL (isTest false). Precompile
  only when connection permission is full. Use when the user asks to publish,
  deploy, apply a change-loop OT on the site, or invokes /publish.
disable-model-invocation: true
---

# Publish (Object Transfer; precompile if full)

Upload Object Transfer JSON and apply it (`isTest: false`). Then `Mutate_admin_precompile` **only** when `.xeelo-connection.json` `permission` is `full`; at `read-write` skip precompile and announce it. Read [AGENT.md](../../AGENT.md) for the full development loop.

Typical order after a change: generate OT → dry-run `--only-test` (automatic, `isTest: true`) → `/publish` (ask or `auto` in conventions) → `/download-db` (ask or `auto`).

Do **not** auto-run `/publish` after generate unless this site’s `conventions.md` has **Publish after dry-run:** `auto`. Otherwise only follow this skill when the user explicitly asks to publish, agrees after you asked, or picks “remember” (then write `auto` into that file — see [AGENT.md § Agent loop](../../AGENT.md#agent-loop-in-conventions)).

This skill does **not** exist as `/push`. Real apply is `/publish` (OT `isTest: false`). Precompile runs only when connection `permission` is **`full`**. For precompile alone, use `/precompile`. There is **no** `Mutate_admin_transfer_process`.

## Prerequisites

- `projects/<project>/.xeelo-connection.json` exists and is filled in:
  - `xeeloUrl`
  - `token` (GraphQL token with `isAdmin`)
  - `permission` — **`read-write`** or **`full`**. Missing/empty = `read-only` → **stop**. Tell the user to set `permission` if they want to publish. Do not change the field unless they ask.
- If the connection file is missing or `xeeloUrl` / `token` is empty, stop and tell the user to complete it first (see `/new-project` checklist).

## Inputs

Determine from the user message or ask once:

- **`<project>`** — project slug under `projects/`. Default to the project mentioned in chat or the one whose connection file is open.
- **JSON or change loop** — explicit `*-object-transfer.json`, or `projects/<project>/changes/<slug>/`.

## Python environment

From repo root, use `.venv/bin/python` when `.venv/` exists. If dependencies are missing (`httpx`, `pyyaml`, …), create the venv and install:

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Use `PYTHON=python` only when system Python already has requirements installed.

## Step 0 — package must exist

If the user pointed at a change loop and `output/*-object-transfer.json` is missing, generate first:

```bash
$PYTHON scripts/generate-change-loop.py \
  projects/<project>/changes/<slug>
```

Then continue. Do not invent a path.

## Step 1 — Publish (apply; precompile if `full`)

The script uploads OT (`isTest: false`). It precompiles **only** when `permission` is `full`. At `read-write` it prints `Precompile skipped` — announce that in chat (`full` or `/precompile` later).

Change loop (all `output/*-object-transfer.json`, sequential, then one precompile if `full`):

```bash
$PYTHON scripts/publish-object-transfer.py \
  --connection projects/<project>/.xeelo-connection.json \
  --loop projects/<project>/changes/<slug>
```

Explicit JSON:

```bash
$PYTHON scripts/publish-object-transfer.py \
  --connection projects/<project>/.xeelo-connection.json \
  --json projects/<project>/changes/<slug>/output/<object>-object-transfer.json
```

Optional `--timeout 600`.

Multiple packages in one loop are uploaded **one after another**, then precompile runs once.

## Output

Report each package from stdout (`Uploaded … success=True`) and either the precompile line (`Precompile success=True`) or `Precompile skipped`.

Failed upload → stop; do not precompile remaining packages if the command already exited non-zero.
Permission `read-only` or script `permission is … (needs read-write or full)` → stop; do not retry.

## On success — next step (`/download-db`)

Read **Download-db after publish** in `projects/<project>/conventions.md` (`ask` | `auto`; missing = `ask`):

- **`auto`** — run `/download-db` to refresh `projects/<project>/env/`. Announce that conventions say so.
- **`ask`** — offer: **Refresh env now** / **Refresh now and remember for this site** / **Don't download**. Do not run unless they pick a refresh option. Remember → set **Download-db after publish** to `auto` in that file (add **Agent loop** if missing).

## Errors

- **Auth / ACCESS_DENIED** — GraphQL token with `isAdmin` required; there is no refresh.
- **Permission** — `read-only` cannot publish. Script exits with `needs read-write or full`. Do not retry until the user sets `permission`.
- **Upload success=false** — report mutation messages; site was not fully applied.
- **Timeout** — GraphQL SQL limit is 10 minutes; retry with higher `--timeout`.
- After precompile GraphQL may restart; the script polls health before exiting. At `read-write`, stdout `Precompile skipped` is success for the OT apply, not a failed precompile.
