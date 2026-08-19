---
name: download-db
description: >-
  Download the latest Xeelo DB transfer ZIP from Admin and extract it into
  projects/<project>/env/. Use when the user asks to download, refresh, or pull
  a DB transfer or snapshot, sync env from Admin, or invokes /download-db.
disable-model-invocation: true
---

# Download DB Transfer & Extract Env

Download the latest DB transfer from Xeelo Admin, then extract `env/` (catalog + shared + object specs). Read [AGENT.md](../../AGENT.md) for the full development loop.

## Prerequisites

- `projects/<project>/.xeelo-connection.json` exists and is filled in:
  - `adminBaseUrl`
  - `siteId` (`XA-SITE-ID`)
  - `credentials` (valid OAuth token JSON)
- If connection file is missing or has empty `siteId` / `credentials`, stop and tell the user to complete it first (see `/new-project` checklist).

## Site vs company

| Term | Meaning | Where |
|------|---------|--------|
| **site** / `siteId` | Xeelo site; Admin API header `XA-SITE-ID` | `.xeelo-connection.json`, download step |
| **company** / `companyId` | Logical object division (`Company` table in DB transfer) | `catalog.yaml`, spec `ids.explicit.companyId` |

Example (lz): `siteId: 8` in connection, company **KB** has `Company.CompanyID: 9001` in DB transfer.

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

Uses `siteId` from the connection file (Admin API only):

```bash
$PYTHON scripts/download-db-transfer.py \
  --connection projects/<project>/.xeelo-connection.json
```

Optional flags:

- `--project projects/<project>` — override project directory (default: parent of connection file)
- `--timeout 3600` — seconds to wait for Admin TempFile (default 3600)

Note the ZIP path from stdout (`Wrote projects/<project>/snapshots/<stamp>/<filename>.zip`).

## Step 2 — Extract env

Run immediately after a successful download, using the ZIP from step 1:

```bash
$PYTHON scripts/extract-db-transfer-to-env.py \
  projects/<project>/snapshots/<stamp>/<filename>.zip \
  -o projects/<project>/env
```

Extract always writes **all** objects from the transfer (every company). Each object spec still records its `companyId` in metadata.

The extract script **materializes the raw XML** from the ZIP into the same snapshot folder (UTF-16 LE, e.g. `lz_20260813_102209.xml` next to the `.zip`). Keep both files — do not delete the XML after extract.

## Output

Report both steps:

1. **Snapshot** — `projects/<project>/snapshots/<stamp>/<filename>.zip` and byte size
2. **Snapshot XML** — `projects/<project>/snapshots/<stamp>/<filename>.xml` (written by extract step)
3. **Env** — `projects/<project>/env/` with catalog object count and list of extracted object slugs from extract stdout

Remove `.gitkeep` files under `env/` if real content was written.

### Empty site is OK

`catalog=0`, `extracted=0` on a **new or empty site** is expected — not a failed extract. `env/` still gets `catalog.yaml`, `shared/*.yaml`, and `extract-summary.yaml`; there is simply no `objects/<slug>/` yet. See [AGENT.md § Empty site](../../AGENT.md). Reference: [`projects/lz/`](projects/lz/) before deploy.

### After greenfield deploy

Expect `catalog=1`, `extracted=1` (e.g. lz Transakce). Reference snapshot: [`projects/lz/snapshots/20260813_132321/`](projects/lz/snapshots/20260813_132321/).

## On success — suggest next step

Offer to start a change loop (`/change-loop` when available) or edit specs under `projects/<project>/env/objects/`.

## Errors

- **Auth / token expired** — ask user to refresh credentials in `.xeelo-connection.json`.
- **Timeout** — DB transfer prep on Admin can take long; retry with higher `--timeout` if needed.
- **Extract fails** — verify the ZIP path.
