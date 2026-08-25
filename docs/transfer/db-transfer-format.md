# DB Transfer Format

Xeelo **Database Transfer** exports whole-site configuration. xeelo-skills **downloads and parses** DB transfers as the environment baseline; it does **not** generate DB transfer ZIPs (re-export always comes from the site via GraphQL `Select_admin_transfer_download`).

## Observed package shape

GraphQL download returns the setup as a **JSON string**. xeelo-skills saves it as **UTF-8**. The payload is one object: each key is a table name, each value is an array of row objects (`FOR JSON PATH`):

```json
{
  "Company": [
    { "CompanyID": 9001, "CompanyName": "Demo", "IsActive": true }
  ],
  "Object": [ { "ObjectID": 9003, "ObjectName": "Invoice", "IsActive": true } ],
  "ObjectLine": []
}
```

| Property | Value |
|----------|--------|
| Encoding | UTF-8 |
| Wrapper | None — no `TransferInfo` / `TransferType` / `Version` |
| Hierarchy | **No** `ObjectSetup` / `ObjectMap` |
| Scope | Whole site configuration (~110 tables) |
| `bit` columns | JSON `true` / `false` |
| `NULL` columns | Omitted from the row |
| Empty table | `[]` |
| Audit columns | `Created*` / `Modified*` are not exported |
| Inactive rows | Tables with `IsActive` export only `IsActive = true` |

Masked columns stay in the row with value `"-"`: `AttachmentStorage` username, password, and connection params; `GeneralVariableValue`.

Parse with:

```bash
python scripts/extract-db-transfer-to-env.py \
  projects/<name>/snapshots/<stamp>/<file>.json \
  -o projects/<name>/env
```

Extract writes catalog, shared (`companies`, `object-types`, `roles`, `statuses`, `sources`, and `custom-colors` when the site has `CustomColor` rows), and **full specs for every object** in the transfer (all companies). `catalog.yaml` `source.transferType` is `DB`; there is no package version field.

Each snapshot folder keeps the UTF-8 JSON file.

## Legacy XML

Older GraphQL downloads were UTF-16 LE concatenated `<XMLData>` blocks (with `TransferInfo`). Older Admin exports were a ZIP of XML. xeelo-skills **does not** parse those shapes anymore.

## Download from GraphQL (xeelo-skills tool)

```bash
python scripts/download-db-transfer.py \
  --connection projects/<name>/.xeelo-connection.json
```

Flow:

1. Load `.xeelo-connection.json` (`xeeloUrl`, GraphQL `token`)
2. `POST {xeeloUrl}/graphql` — `Select_admin_transfer_download { json }` (`Authorization: Bearer <token>`)
3. Validate the string is a JSON object, write UTF-8 to `projects/<project>/snapshots/<stamp>/`

## Use in xeelo-skills

| Purpose | Resource |
|---------|----------|
| Download | [`scripts/download-db-transfer.py`](../../scripts/download-db-transfer.py) |
| Parse / env extract | [`scripts/extract-db-transfer-to-env.py`](../../scripts/extract-db-transfer-to-env.py) |
| Table columns / FKs | [`data/schemas/`](../data/schemas/) |
| Full table list | [`data/transfer-tables.json`](../data/transfer-tables.json) |
| Field hints | [`data/table-hints.json`](../data/table-hints.json) |
| **Generate deployable changes** | [Object Transfer](object-transfer-format.md) (same JSON shape, subset of tables) |

## Import behaviour (DB transfer)

- Export includes **whole configuration**, **not** user requests
- **Process** deletes and replaces existing configuration
- Database is **locked** during processing
- **Users / UserAccess** are not transferred

Admin DB-transfer **import** (process batch) is a separate XML pipeline. xeelo-skills does not generate or upload DB transfers.

## Table types

Process-batch table roles:

- **U** — unit (parent)
- **D** — detail (child)
- **X** — cross-reference / value table
