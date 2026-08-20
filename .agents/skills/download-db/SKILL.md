---
name: download-db
description: >-
  Download the latest Xeelo DB transfer XML via GraphQL and extract it into
  projects/<project>/env/. Use when the user asks to download, refresh, or pull
  a DB transfer or snapshot, sync env from the site, or invokes /download-db.
disable-model-invocation: true
---

# Download DB Transfer & Extract Env

Download the latest DB transfer from Xeelo GraphQL (`Select_admin_transfer_download`), then extract `env/` (catalog + shared + object specs). Read [AGENT.md](../../AGENT.md) for the full development loop.

## Prerequisites

- `projects/<project>/.xeelo-connection.json` exists and is filled in:
  - `xeeloUrl` — Xeelo site URL (User UI)
  - `token` — fixed GraphQL **admin** Bearer token (`isAdmin`; no refresh)
- If the connection file is missing or `xeeloUrl` / `token` is empty, stop and tell the user to complete it first (see `/new-project` checklist). If the loader rejects the file, tell the user to **replace** it with `{ "xeeloUrl": "...", "token": "..." }`.

## Site vs company

| Term | Meaning | Where |
|------|---------|--------|
| **site** | Xeelo instance identified by `xeeloUrl` + token | `.xeelo-connection.json` |
| **company** / `companyId` | Logical object division (`Company` table in DB transfer) | `catalog.yaml`, spec `ids.explicit.companyId` |

Example (lz): company **KB** has `Company.CompanyID: 9001` in DB transfer.

## Inputs

Determine from the user message or ask once:

- **`<project>`** — project slug under `projects/` (e.g. `lz`, `ovnet`). Default to the project mentioned in chat or the one whose connection file is open.

## Python environment

From repo root, use `.venv/bin/python` when `.venv/` exists. If dependencies are missing (`httpx`, `pyyaml`, …), create the venv and install:

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Use `PYTHON=python` only when system Python already has requirements installed.

## Step 1 — Download

```bash
$PYTHON scripts/download-db-transfer.py \
  --connection projects/<project>/.xeelo-connection.json
```

Optional flags:

- `--project projects/<project>` — override project directory (default: parent of connection file)
- `--timeout 600` — HTTP timeout seconds (default 600; GraphQL SQL limit is 10 minutes)

Note the XML path from stdout (`Wrote projects/<project>/snapshots/<stamp>/<project>_<stamp>.xml`).

## Step 2 — Extract env

Run immediately after a successful download, using the XML from step 1:

```bash
$PYTHON scripts/extract-db-transfer-to-env.py \
  projects/<project>/snapshots/<stamp>/<filename>.xml \
  -o projects/<project>/env
```

Extract always writes **all** objects from the transfer (every company). Each object spec still records its `companyId` in metadata.

The extract script also accepts a ZIP (legacy Admin snapshots). New downloads are XML only — keep the XML; do not delete it after extract.

## Output

Report both steps:

1. **Snapshot XML** — `projects/<project>/snapshots/<stamp>/<filename>.xml` and byte size
2. **Env** — `projects/<project>/env/` with catalog object count and list of extracted object slugs from extract stdout

Remove `.gitkeep` files under `env/` if real content was written.

### Empty site is OK

`catalog=0`, `extracted=0` on a **new or empty site** is expected — not a failed extract. `env/` still gets `catalog.yaml`, `shared/*.yaml`, and `extract-summary.yaml`; there is simply no `objects/<slug>/` yet. See [AGENT.md § Empty site](../../AGENT.md). Reference: [`projects/lz/`](projects/lz/) before deploy.

### After greenfield deploy

Expect `catalog=1`, `extracted=1` (e.g. lz Transakce). Reference snapshot: [`projects/lz/snapshots/20260813_132321/`](projects/lz/snapshots/20260813_132321/).

## On success — suggest next step

Offer to start a change loop (`/change-loop` when available) or edit specs under `projects/<project>/env/objects/`.

## Errors

- **Auth / ACCESS_DENIED** — token is missing `isAdmin`. Ask the user to put an admin GraphQL token in `.xeelo-connection.json`. There is no refresh.
- **Timeout** — large-site download can take up to 10 minutes on GraphQL; retry with higher `--timeout` if needed.
- **Extract fails** — verify the XML path.
