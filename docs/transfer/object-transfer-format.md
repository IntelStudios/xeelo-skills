# Object Transfer Format

Xeelo Admin **Object Transfer** exports one or more objects and their dependency subtree as a **single XML file** inside a ZIP.

## Why Object Transfer (vs DB Transfer)

| Feature | Object Transfer | DB Transfer |
|---------|-----------------|-------------|
| Scope | Selected object(s) + dependencies | Entire site (~110 tables) |
| Apply | **Partial** — select rows in tree | Full replace |
| Hierarchy | `ObjectSetup` + `ObjectMap` tree | Flat table list |
| Upload type | `TransferType=OBJECT` | `TransferType=DB` |

xeelo-skills **generates Object Transfer**. DB transfer docs/schemas are kept as **reference** for table/column semantics only.

## ZIP contents

One XML file (e.g. `object-transfer.xml`) inside the ZIP — not one file per table.

## XML structure

Xeelo Admin export uses **concatenated `<XMLData>` blocks** (UTF-16 LE with BOM, no `<?xml` declaration). Upload SP (`spAdminObjectSetupXMLUpload`) parses **each block separately** — a single monolithic block breaks import.

```text
<XMLData>...all ObjectSetup edges...</XMLData>
<XMLData>...all ObjectMap pairs (~124)...</XMLData>
<XMLData><TransferInfo>...</TransferInfo></XMLData>
<XMLData>...ObjectType rows...</XMLData>
<XMLData>...Object rows...</XMLData>
<XMLData>...ObjectLine rows...</XMLData>
...
```

Golden references:

- Generated: [`projects/account-object/output/object-transfer.xml`](../../projects/account-object/output/object-transfer.xml)
- Xeelo export: [`projects/cars/ObjectSetup_20260811_084036.xml`](../../projects/cars/ObjectSetup_20260811_084036.xml)

Validate output:

```bash
make validate-account
# or
python scripts/validate-object-transfer.py path/to/object-transfer.xml
```

Upload **rejects** packages unless:
- `TransferType = OBJECT`
- `Version` matches site `OT_Version` (currently `1.3.0`)

## Hierarchy edges (ObjectSetup)

Each edge links a **parent row** to a **child row** in the admin tree.

Layout chain for form fields:

```
Object → ObjectLine → ObjectLineTab → ObjectLineSection
Object → ObjectLineOnGrid  (direct; references ObjectLineID)
Object → ObjectDefault → ObjectDefaultLine → ObjectLineLookup → ObjectLineLookupValue
ObjectDefaultLine → ObjectLineAutoNumber
Object → Workflow → WorkflowStep → WorkflowStepAction
```

Schema pairs (ObjectMap): full map from [`data/object-transfer-map.json`](../../data/object-transfer-map.json) (~124 parent→child table types), same as Xeelo download. Generator also adds `Parent → LanguageTable` pairs when `spec/language-table.yaml` is present.

## Partial deployment

KB `/publish` applies the generated package (all rows, Orig. ID) then precompiles. Manual Admin UI still works for selecting rows:

1. Upload ZIP in Admin → **Object Transfer**
2. Review hierarchy tree — uncheck rows not ready (`IsSelected=0`)
3. Per row: **Import as New** (`IsCreateNewID=1`) or **Import with Orig. ID** (`=0`, default)
4. **Process** — only selected rows apply
5. Repeat with next batch

Generator defaults match upload SP: all rows included, Orig. ID mode.

## Publish from xeelo-skills

After generate, the loop **automatically** dry-runs the transfer (`isTestOnly: true`). `/publish` is the real apply + precompile (`ask` unless **Publish after dry-run** in the site’s `conventions.md` is `auto`).

```bash
# Dry-run (automatic after generate)
python scripts/push-object-transfer.py \
  --connection projects/<project>/.xeelo-connection.json \
  --loop projects/<project>/changes/<slug> \
  --only-test

# Real process + precompile (/publish)
python scripts/publish-object-transfer.py \
  --connection projects/<project>/.xeelo-connection.json \
  --loop projects/<project>/changes/<slug>

# Precompile only (/precompile)
python scripts/precompile-settings.py \
  --connection projects/<project>/.xeelo-connection.json
```

Dry-run / publish transfer flow (GraphQL, synchronous, 10 min SQL timeout):

1. Load `.xeelo-connection.json` (`xeeloUrl`, admin `token`)
2. `Mutate_admin_transfer_upload(fileName, xml)` — XML as GraphQL string (UTF-16 LE on the server)
3. `Mutate_admin_transfer_process(id, isTestOnly)` — `true` for dry-run, `false` for `/publish`

`/publish` then:

4. `Mutate_admin_precompile`
5. Poll `{xeeloUrl}/graphql-api/health` until GraphQL is back (process may restart)

Skills: [`.agents/skills/publish/SKILL.md`](../../.agents/skills/publish/SKILL.md), [`.agents/skills/precompile/SKILL.md`](../../.agents/skills/precompile/SKILL.md).

## Import modes

| Mode | Flag | When to use |
|------|------|-------------|
| Import with Orig. ID | `IsCreateNewID=0` | Known IDs, replace existing row |
| Import as New | `IsCreateNewID=1` | Clone object on target site |

## Reference data

`Role` and `RequestStatus` are defined in spec (`roles` / `statuses`) and **always emitted** in transfer together with `Company` and `ObjectType`.

`LanguageTable` (translated labels) is a child of the owning entity. Spec: [`spec/language-table.yaml`](spec-format.md#localization-speclanguage-tableyaml). After process, **/publish** (or `/precompile` if the OT is already applied).

## Generate

```bash
python scripts/generate-object-transfer.py projects/account-object/xeelo-spec.yaml \
  -o projects/account-object/output/object-transfer.xml \
  --zip projects/account-object/account-object-transfer.zip
```

Golden example: [`projects/account-object/output/object-transfer.xml`](../../projects/account-object/output/object-transfer.xml)

## onGrid in transfer

Two layers:

1. **ObjectLine** — display flags (`ObjectLineOnGridIsAllowed`, `ObjectLineOnGridName`, `ObjectLineOnGridIsTag`, …)
2. **ObjectLineOnGrid** — placement per layout variant (`Size` × `Type` × `Module`). `Type` is `Grid` or `Table`; Table is one visual row (spec pseudo-rows do not wrap — horizontal scroll).

Spec: `onGrid.fields` + `onGrid.layouts` in [`spec-format.md`](spec-format.md)
