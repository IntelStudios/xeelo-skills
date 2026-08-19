# DB Transfer Format

Xeelo Admin **Database Transfer** exports whole-site configuration. XeeloKB **downloads and parses** DB transfers as the environment baseline; it does **not** generate DB transfer ZIPs (re-export always comes from Admin).

## Observed package shape (current Admin)

Modern Admin export is a **ZIP with one UTF-16 LE XML** (BOM), containing **concatenated `<XMLData>` blocks** — one block per table (all rows of that table inside the block):

```text
<XMLData><TransferInfo><TransferType>DB</TransferType><Version>1.3.0</Version></TransferInfo></XMLData>
<XMLData><Company>...</Company><Company>...</Company></XMLData>
<XMLData><Object>...</Object>...</XMLData>
...
```

| Property | Value |
|----------|--------|
| Encoding | UTF-16 LE + BOM |
| `TransferType` | `DB` |
| Hierarchy | **No** `ObjectSetup` / `ObjectMap` (unlike Object Transfer) |
| Scope | Whole site configuration (~90–110 tables) |

Golden samples:

- Populated site: [`projects/ovnet/snapshots/`](../../projects/ovnet/snapshots/)
- Empty / fresh site: [`projects/lz/env/`](../../projects/lz/env/) (`catalog=0`, no `objects/` tree — normal)

Parse with (writes raw XML alongside the ZIP under `snapshots/<stamp>/`):

```bash
python scripts/extract-db-transfer-to-env.py \
  projects/ovnet/snapshots/<stamp>/<name>.zip \
  -o projects/ovnet/env
```

Extract writes catalog, shared, and **full specs for every object** in the transfer (all companies).

Each snapshot folder keeps **both** the Admin ZIP and the extracted XML (UTF-16 LE multi-block `<XMLData>` file) for diffing, debugging, and re-parse without unzipping.

## Legacy / alternate shape

Older docs describe a ZIP of **one UTF-8 XML file per table** plus `TransferInfo.xml`. Treat that as historical; prefer the multi-block UTF-16 package above when present.

## Download from Admin (XeeloKB tool)

```bash
python scripts/download-db-transfer.py \
  --connection projects/ovnet/.xeelo-connection.json
```

Flow:

1. Refresh token — `POST /token` (`grant_type=refresh_token`)
2. Connect WebSocket — `ws(s)://{host}/api/ws?access_token=...`
3. Start prep — `GET /api/SiteAdmin/XeeloSetup` with `Authorization` + `XA-SITE-ID` (= `siteId` from connection)
4. Wait for notification `Type=TempFile`, `Status=Success`, `Params.id`
5. Download — `GET /api/SuperAdmin/General/AdminTempFile/{id}` → `projects/<project>/snapshots/`

## Use in XeeloKB

| Purpose | Resource |
|---------|----------|
| Download | [`scripts/download-db-transfer.py`](../../scripts/download-db-transfer.py) |
| Parse / env extract | [`scripts/extract-db-transfer-to-env.py`](../../scripts/extract-db-transfer-to-env.py) |
| Table columns / FKs | [`data/schemas/`](../data/schemas/) |
| Full table list | [`data/transfer-tables.json`](../data/transfer-tables.json) |
| Field hints | [`data/table-hints.json`](../data/table-hints.json) |
| **Generate deployable changes** | [Object Transfer](object-transfer-format.md) |

## Import behaviour (DB transfer)

- Export includes **whole configuration**, **not** user requests
- **Process** deletes and replaces existing configuration
- Database is **locked** during processing
- **Users / UserAccess** are not transferred

## Table types

From `spAdminDbSetupXMLProcessBatch.sql`:

- **U** — unit (parent)
- **D** — detail (child)
- **X** — cross-reference / value table
