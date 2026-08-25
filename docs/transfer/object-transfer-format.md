# Object Transfer Format

xeelo-skills **generates Object Transfer** as UTF-8 JSON and applies it through GraphQL. The payload uses the **same table→rows shape as DB-transfer download**, but **only changing rows**.

A row is omitted when its Orig. ID already exists in the latest site snapshot **and** every generated cell matches that download row. Other rows may still reference that ID (`Object.CompanyID`, `ObjectDefault.WorkflowID`, …). New rows and rows whose generated cells differ are emitted. Generate diffs against `projects/<site>/snapshots/` (override with `--baseline`, skip with `--no-baseline`).

`workflow.reuse: true` also skips **generating** the shared `Workflow` / `WorkflowStep` / `WorkflowStepAction` definition so a copied spec cannot upsert the process. New object lines still get `WorkflowStepAccess` on the shared steps.

## Why Object Transfer (vs DB Transfer)

| Feature | Object Transfer | DB Transfer |
|---------|-----------------|-------------|
| Scope | Selected object(s) + dependencies | Entire site (~110 tables) |
| Apply | **Partial** — generated rows only | Full replace (Admin DB import) |
| Shape | JSON object keyed by table name | Same JSON shape |
| GraphQL | `Mutate_admin_transfer_upload` | `Select_admin_transfer_download` |

DB transfer docs/schemas are **reference** for table/column semantics. xeelo-skills does not generate or upload DB transfers.

## JSON structure

One UTF-8 object. Each key is a table name; each value is a non-empty array of row objects. No `TransferInfo`, `ObjectSetup`, or `ObjectMap`. Empty tables and `null` cells are omitted. `bit` columns are JSON `true` / `false`.

```json
{
  "Object": [
    { "ObjectID": 1, "ObjectName": "Account", "IsActive": true }
  ],
  "ObjectLine": [
    { "ObjectLineID": 10, "ObjectID": 1, "ObjectLineName": "Name", "IsActive": true }
  ]
}
```

Change-loop generator emits **one JSON file per touched object** (`output/<slug>-object-transfer.json`), Orig. ID rows.

## Publish from xeelo-skills

After generate, the loop **automatically** dry-runs (`isTest: true`). `/publish` applies for real (`isTest: false`) then precompiles (`ask` unless **Publish after dry-run** in the site’s `conventions.md` is `auto`).

```bash
# Dry-run (automatic after generate) — CLI flag --only-test maps to isTest
python scripts/push-object-transfer.py \
  --connection projects/<project>/.xeelo-connection.json \
  --loop projects/<project>/changes/<slug> \
  --only-test

# Real apply + precompile (/publish)
python scripts/publish-object-transfer.py \
  --connection projects/<project>/.xeelo-connection.json \
  --loop projects/<project>/changes/<slug>

# Precompile only (/precompile)
python scripts/precompile-settings.py \
  --connection projects/<project>/.xeelo-connection.json
```

GraphQL flow (synchronous, 10 min SQL timeout):

1. Load `.xeelo-connection.json` (`xeeloUrl`, admin `token`)
2. `Mutate_admin_transfer_upload(json, isTest)` — JSON string of table→rows; `isTest: true` dry-run, `false` apply. There is **no** separate process mutation.
3. `/publish` then `Mutate_admin_precompile` and poll `{xeeloUrl}/graphql-api/health` (process may restart)

```graphql
mutation AdminTransferUpload($json: String!, $isTest: Boolean!) {
  Mutate_admin_transfer_upload(json: $json, isTest: $isTest) {
    success
    messages { procedure msgType msgText }
  }
}
```

Skills: [`.agents/skills/publish/SKILL.md`](../../.agents/skills/publish/SKILL.md), [`.agents/skills/precompile/SKILL.md`](../../.agents/skills/precompile/SKILL.md).

## Table relationships (no ObjectSetup in JSON)

FK columns on the rows replace the old XML `ObjectSetup` tree. Typical chains:

```
Object → ObjectLine → ObjectLineTab → ObjectLineSection
Object → ObjectLineOnGrid  (direct; references ObjectLineID)
Object → ObjectDefault → ObjectDefaultLine → ObjectLineLookup → ObjectLineLookupValue
ObjectDefaultLine → ObjectLineAutoNumber
Object → Workflow → WorkflowStep → WorkflowStepAction
```

Schema pairs: [`data/object-transfer-map.json`](../../data/object-transfer-map.json).

## Partial deployment

`/publish` applies the generated JSON (all rows in the file, Orig. ID) then precompiles.

## Import modes

Generator emits Orig. ID rows (replace existing). Cloning as new IDs is an Admin-UI concern, not the GraphQL JSON path.

## Reference data

`Role` and `RequestStatus` live in spec (`roles` / `statuses`) so steps can use keys. Generate emits those tables only when the row is new or changed vs download — same rule as `Company`, `ObjectType`, `Workflow`, and every other table.

`LanguageTable` (translated labels) is a child of the owning entity. Spec: [`spec/language-table.yaml`](spec-format.md#localization-speclanguage-tableyaml). After apply, **/publish** (or `/precompile` if the OT is already applied).

`TableComments` (Admin HTML notes) is the same polymorphic pattern (`TableName` + `TableRowID`). Spec: [`spec/comments.yaml`](spec-format.md#admin-comments-speccommentsyaml). Upsert by Orig. ID; omitted comments stay.

## Generate

```bash
python scripts/generate-object-transfer.py projects/<name>/xeelo-spec.yaml \
  -o projects/<name>/output/object-transfer.json
```

## onGrid in transfer

Two layers on the **object** (inbox):

1. **ObjectLine** — display flags (`ObjectLineOnGridIsAllowed`, `ObjectLineOnGridName`, `ObjectLineOnGridIsTag`, …)
2. **ObjectLineOnGrid** — placement per layout variant (`Size` × `Type` × `Module`). Either `ObjectLineID` (spec `field`) or `SystemLineID` (spec `systemLine`) — not both.

**Subgrid** analog (not in spec/generate today):

1. **ObjectSubLine** — `ObjectSubLineOnGridIsAllowed`, `ObjectSubLineOnGridName`, `ObjectSubLineOnGridIsTag`, `ObjectSubLineIsSearch`, `ObjectSubLineIsTotal`
2. **ObjectSubLineOnGrid** — placement (`Size` × `Type` × `Module`). `ObjectSubLineID` only — no `SystemLineID`.

Which triples exist, Grid vs Table, and rows `T`/`A`–`E`: [ongrid.md](../entities/ongrid.md). Spec YAML: [`spec-format.md`](spec-format.md#ongrid).

## Legacy XML

Older Object Transfers were UTF-16 LE concatenated `<XMLData>` blocks (`ObjectSetup`, `ObjectMap`, `TransferInfo`, `TransferType=OBJECT`, `Version=1.3.0`) inside a ZIP. Admin UI upload/process of that XML still exists separately. xeelo-skills GraphQL **does not** send XML. `extract-object-transfer-to-spec.py` and `validate-object-transfer.py` still read legacy XML.
