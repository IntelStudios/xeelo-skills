# DB Transfer Format

Xeelo **Database Transfer** exports whole-site configuration. XeeloKB **downloads and parses** DB transfers as the environment baseline; it does **not** generate DB transfer ZIPs (re-export always comes from the site via GraphQL `Select_admin_transfer_download`).

## Observed package shape

GraphQL download returns the setup XML as a string; XeeloKB saves it as **UTF-16 LE with BOM**. The file contains **concatenated `<XMLData>` blocks** — one block per table (all rows of that table inside the block):

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

Parse with:

```bash
python scripts/extract-db-transfer-to-env.py \
  projects/ovnet/snapshots/<stamp>/<name>.xml \
  -o projects/ovnet/env
```

Extract writes catalog, shared (`companies`, `object-types`, `roles`, `statuses`, `sources`, and `custom-colors` when the site has `CustomColor` rows), and **full specs for every object** in the transfer (all companies).

Each snapshot folder keeps the UTF-16 LE multi-block `<XMLData>` file. Legacy Admin ZIP snapshots still extract if present (the extract script writes XML alongside the ZIP).

## Legacy / alternate shape

Older Admin exports were a **ZIP with one UTF-16 LE XML**. Older docs also describe a ZIP of **one UTF-8 XML file per table** plus `TransferInfo.xml`. Treat both as historical; new `/download-db` writes XML only.

## Download from GraphQL (XeeloKB tool)

```bash
python scripts/download-db-transfer.py \
  --connection projects/ovnet/.xeelo-connection.json
```

Flow:

1. Load `.xeelo-connection.json` (`xeeloUrl`, GraphQL admin `token`)
2. `POST {xeeloUrl}/graphql` — `Select_admin_transfer_download { xml }` (`Authorization: Bearer <token>`)
3. Write UTF-16 LE XML to `projects/<project>/snapshots/<stamp>/`

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
