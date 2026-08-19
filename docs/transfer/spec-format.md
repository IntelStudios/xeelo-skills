# Xeelo Spec Format (v2)

**Xeelo Spec** is the agent's structured input before generating **Object Transfer** XML. It may be a single YAML file or a **multi-file** directory with an entry `xeelo-spec.yaml` and `includes`.

JSON Schema (merged spec): [`schema/xeelo-spec.schema.json`](../../schema/xeelo-spec.schema.json)

## Multi-file layout (Account)

```
projects/account-object/
  xeelo-spec.yaml       # metadata + includes
  spec/
    object.yaml         # object, company, layout, onGrid
    workflow.yaml       # workflow
    ids.yaml            # ids (+ source after extract)
```

**Entry** [`projects/account-object/xeelo-spec.yaml`](../../projects/account-object/xeelo-spec.yaml):

```yaml
version: 2
kind: create_object
transferType: object
transferVersion: "1.3.0"

includes:
  - spec/object.yaml
  - spec/workflow.yaml
  - spec/ids.yaml
```

**Fragment** `spec/object.yaml`:

```yaml
object:
  name: Account
  code: ACCOUNT
  objectType: Finance
company:
  name: Finance Company
layout:
  tabs:
    - name: General
      placement: 0
      order: 1
      sections:
        - name: Details
          order: 1
          width: 100
          fields:
            - name: Account Number
              code: ACCOUNT_NUMBER
              type: text
              slot: 1
              width: 50
              mandatory: true
onGrid:
  fields:
    ACCOUNT_NUMBER:
      allowed: true
      name: Account No
  layouts: [...]
```

Generator and extract use [`scripts/ot_builder/spec_loader.py`](../../scripts/ot_builder/spec_loader.py) — `load_spec(path)` accepts a file or directory; monolithic YAML without `includes` still works.

## Top-level fields

| Field | Required | Description |
|-------|----------|-------------|
| `version` | yes | Must be `2` |
| `kind` | yes | `create_object` |
| `transferType` | no | `object` (default) |
| `object` | yes | Object identity (`name`, `code`, `objectType`) |
| `company` | yes | Company row in transfer (`name`) |
| `layout.tabs[]` | yes | Tabs with nested sections and fields |
| `onGrid` | no | Inbox grid display + placement (typically in `object.yaml`) |
| `workflow` | no | Defaults to minimal 2-step flow |
| `ids.base` | no | Per-table max PK for **new** rows (`ObjectLine: 9112` → next is 9113). Omit for greenfield (default 9000 per table). Legacy: a single integer is the default for tables not in the map. |
| `ids.explicit` | no | Stable IDs from site / transfer (see below) |
| `ids.byTable` | no | This object's ID inventory from extract |
| `source` | no | Provenance after extract from transfer |
| `transferVersion` | no | `OT_Version` — default `1.3.0` |

Generator **always** creates `Company`, `ObjectType`, `Role`, and `RequestStatus` rows from spec definitions and `ids.explicit`.

## Layout: tabs → sections → fields

Each object can have **multiple tabs** (left/right via `placement`) and **multiple sections** per tab.

Fields are defined inside their section under `layout.tabs[]`.

### Section properties

| Property | Maps to |
|----------|---------|
| `name` | `ObjectSectionName` |
| `order` | `ObjectSectionOrder` |
| `width` | `ObjectSectionWidth` — section width in percent (1–100, default 100) |

### Field properties

| Property | Maps to |
|----------|---------|
| `name` | `ObjectLineName` |
| `code` | `ObjectLineCode` (also used in `onGrid`) |
| `type` | `ObjectLineTypeID` via [`field-type-mapping.json`](../../data/field-type-mapping.json) — all 20 slugs in [object-line-types.md](../entities/object-line-types.md) |
| `slot` | `ObjectLineSlot` (unique per object; not required for types 5, 6, 13, 16, 17) |
| `width` | `ObjectLineTypeWidth` — field width in **percent** (1–100) |
| `order` | `ObjectLineOrder` |
| `mandatory` | `ObjectDefaultLineValidationID = 1` (default template unless overridden in `templates`). Omit `mandatory`/`extended` → still emit **`ValidationID = 2`** (Optional); do not leave the column unset |
| `precision` | `ObjectLineNumberPrecision` (number fields) |
| `numberSeparator` / `numberMin` / `numberMax` | Number extras |
| `reference` | `ObjectLineSource` on **ObjectLine** (číselník) — combo, radio, multi |
| `lookup` | `ObjectLineLookup` on **template line** (dotazovací mapa) |
| `objectSubId` | `ObjectLine.ObjectSubID` (subgrid fields) |
| `saveAction` | `ObjectLineButtonSaveAction` (button fields) |
| `attachmentStorageId`, `ocr`, `ocrLang`, `imageResizeMax`, `mobileScan`, `mobileSignature` | Attachment extras |
| `previewField`, `previewDownload` | Attachment preview (`previewField` = attachment field **code**) |
| `webFrameTypeId` | `WebFrameTypeID` (1–4) |
| `textInputType` | `ObjectLineTextInputType` (0 Default, 1 Bar Code, 2 Location) |
| `columnNumbers` | `ObjectLineNumberColumns` (radio / multi) |
| `height` | `ObjectLineHeight` (memo, report) |
| `uniqueId` | `ObjectLineUniqueID` (1–4) |
| `descMemoBorder`, `descMemoPadding` | Description memo extras. **`descMemoBorder` defaults to false** (Admin/SQL `0`); omit it or set `false`. Use `true` only when the user wants a visible box. |
| `buttonMessage`, `colorFont`, `colorBack` | Button extras |
| `isReferenceLink` | `ObjectLineIsReferenceLink` (combo types) |

**Never** `reference` and `lookup` on the same field.

## Reference and sources

Top-level `sources` map defines greenfield reference sources. Fields use `reference.sourceId` (site ID) or `reference.source` (key).

| Režim | `sources` shape | Emit |
|-------|-----------------|------|
| system | (none — only `reference.sourceId`) | FK on ObjectLine only |
| fixed values | `sources.{key}.values[]` | ObjectLineSource + ObjectLineSourceValue |
| refObject | `sources.{key}.refObject` | ObjectLineSource + ObjectLineSourceRefObject |

New `sources.*` default **`styleId: 4`** (Value / `ObjectLineSourceStyleID`). Explicit `styleId` in spec wins. System sources (`reference.sourceId`) are not restyled.

```yaml
sources:
  colors:
    name: Colors
    typeId: 1
    styleId: 4
    values:
      - { value: "1", label: Red }

# field:
reference:
  source: colors
# or site system list:
reference:
  sourceId: 1
```

See [`recipes/add-reference-field.md`](../../recipes/add-reference-field.md).

## IDs and round-trip

Each SQL table has its own identity. After Object Transfer import, Xeelo may assign **different IDs** (`Import as New`). Store them in spec so the next generate uses **Import with Orig. ID**.

### `ids.base`

High-water **per table** for allocating **new** Orig. IDs. Extract from a DB transfer writes the site-wide `max(PK)` of every table in the transfer (not just this object's subtree). Object Transfer extract writes max from tables present in that ZIP.

```yaml
ids:
  base:
    Object: 9100
    ObjectLine: 9112
    ObjectLineOnGrid: 9143
    ObjectAction: 9132
    ObjectDefaultLine: 15
```

A new `ObjectLine` is 9113; a new `ObjectDefaultLine` is 16; a new `ObjectAction` is 9133. Tables not listed start at **9000**.

Legacy `ids.base: 9000` (integer) is still valid: it is the default start for every table that has no map entry and no `byTable` max.

### `ids.explicit`

Structured map keyed by tab name, field `code`, workflow step name, etc.:

```yaml
ids:
  base:
    Object: 9003
    ObjectLine: 9005
    ObjectDefaultLine: 9006
  explicit:
    companyId: 9001
    objectTypeId: 9002
    objectId: 9003
    tabs:
      General: 9004
    sections:
      General/Details: 9004
    fields:
      ACCOUNT_NUMBER: 9005
    objectDefaultLines:
      ACCOUNT_NUMBER: 9006
    sources:
      colors: 9010
    sourceValues:
      "1": 9011
    sourceRefObjects:
      colors: 9012
    refObjectLines:
      line_other_id: 12301
    workflowId: 9018
    roles:
      requestor: 1
      owner: 2
    statuses:
      draft: 1
      active: 2
      completed: 3
    workflowSteps:
      Draft: 9019
    workflowStepActions:
      Submit: 9021
    objectDefaultId: 9024
    objectDefaultExternalLink: 460C2BE0-C28D-426E-A657-C639DAE106CD
    objectDefaultAccessOwnerLevel: 0
    objectDefaultIsExternal: 0
    objectLineOnGrid:
      ACCOUNT_NUMBER: 9024
```

Section keys use `{tabName}/{sectionName}`.

### `ids.byTable`

Complete ID inventory **for this object** from transfer extract (includes ObjectAction, Periodic, ObjectSub, …):

```yaml
ids:
  byTable:
    ObjectLine:
      "11112": 11112
    WorkflowStep:
      "4684": 4684
```

Generator uses `explicit` for existing row IDs. `byTable` seeds per-table used-sets and, when `ids.base` has no entry for a table, the max in `byTable[table]` is that table's high-water. `ids.base` from a DB extract is **site-wide** and wins over this object's `byTable` max so a new ID cannot collide with another object.

## Roles and statuses

Define in `spec/workflow.yaml` (or top-level in monolithic spec). Workflow steps and actions reference **keys**, not numeric IDs:

```yaml
roles:
  requestor:
    name: Requestor MF
    isRequestor: true
  owner:
    name: Requestor
    isRequestor: true

statuses:
  draft:
    name: Saved
    order: 10
  active:
    name: Saved
    order: 20
  completed:
    name: Completed
    isCompleted: true
    order: 10

workflow:
  mode: full
  steps:
    - name: Draft
      role: requestor
      status: draft
      actions:
        - name: Submit
          role: owner
          status: active
          styleId: 1
```

Keys are required when two statuses share the same `name` (e.g. two `Saved` rows on site). Optional `isActive: false` preserves site inactive rows on refactor.

## Workflow modes

### `minimal`

Implicit Draft → Active with Submit / Complete. Requires `roles` / `statuses` with keys `requestor`, `owner`, `draft`, `active`, `completed` (or omit — generator uses defaults).

### `full` (Cars, Account)

```yaml
workflow:
  mode: full
  name: NEW WF testing
  steps:
    - name: Draft
      role: owner
      status: active
      actions:
        - name: Submit
          role: owner
          status: active
          styleId: 1
      access:
        - field: LOAD_TX
          editable: true
```

`steps[].access` maps to **WorkflowStepAccess** (editable/visible per line on that step). Site refresh inserts missing rows as visible + **not** editable. Extract omits those defaults; only emit lines that must be editable (or hidden). Admin UI groups this by request status name (e.g. Open).

**IDs:** `ids.explicit.workflowStepAccess` keys `{stepName}/{field}`. After the first site refresh, reuse the existing `WorkflowStepAccessID` (Orig. ID) — do not allocate a new one or the unique `(WorkflowStepID, ObjectLineID)` index will fail.

Extract sets `mode: full` when steps differ from minimal template **or** any step has non-default access.

## Update actions (`spec/update-actions.yaml`)

Optional fragment for **ObjectUpdateAction** (user update → new request version). See [entities/update-actions.md](../entities/update-actions.md).

```yaml
# xeelo-spec.yaml
includes:
  - spec/object.yaml
  - spec/workflow.yaml
  - spec/update-actions.yaml   # optional
  - spec/ids.yaml
```

```yaml
updateActions:
  - key: amend-address
    name: Amend address
    order: 10
    template: default              # ObjectDefault scope; omit = all templates
    workflow: post_update_wf       # optional; omit = template workflow
    isQuick: false
    tabFocus:
      left: General
      right: null
    access:
      - field: IP_ADDRESS
        editable: true
        visible: true
    conditions:
      - field: STATUS
        type: equals_text
        param1: Active
    messages:
      - key: warning_msg
        visible: true
```

**IDs in `ids.explicit`:**

```yaml
updateActions:
  amend-address: 2401
objectUpdateAccess:
  amend-address/IP_ADDRESS: 5501
objectUpdateActionConditions:
  amend-address/STATUS/equals_text: 5601
objectUpdateMessages:
  amend-address/warning_msg: 5701
objectMessages:
  warning_msg: 1053
```

Condition `type` slugs match platform seed (`contains`, `equals_text`, `is_empty`, …). Extract omits access rows at DB defaults (editable=0, visible=1).

**Not in spec v1:** `ObjectUpdateActionUserList` (User admin only).

## Templates (`spec/templates.yaml`)

Optional fragment for multiple **ObjectDefault** rows. Omit it to keep a single default template (current behaviour; field `mandatory` applies there).

```yaml
templates:
  - key: cash_register
    name: Cash register
    isDefault: true
    fields:
      TYPE: { hidden: true }
  - key: bank
    name: Bank
    fields:
      TYPE: { mandatory: true }
      FIO_API_KEY:
        extended:
          hidden: "id{TYPE} != {account_type.FIO}"
      TOTAL:
        defaultValue: "0"
        clientCalculation:
          type: math
          expr: "id{QTY} * id{PRICE}"
```

| Spec | Maps to |
|------|---------|
| `hidden: true` | `ObjectDefaultLineValidationID = 9`, `ExtHiddenCondition = true` |
| `mandatory: true` | `ObjectDefaultLineValidationID = 1` (unless extended is also set) |
| *(neither `mandatory` nor `extended`)* | `ObjectDefaultLineValidationID = 2` (Optional) — always written; omitting the column is `NULL` and Admin autosaves |
| `extended.hidden/disabled/mandatory` | Independent boolean `condition` expressions (no `v#` prefix) — [xeelo-grammar.md](../entities/xeelo-grammar.md#extended-validation) |
| `clientCalculation.type` / `expr` | Client-Math (`math`) / Client-String (`string`) — stored **without** `1#`/`2#` — [xeelo-grammar.md](../entities/xeelo-grammar.md#client-math-vs-client-string). Client-UserInfo (`user_info`) / Client-DeviceInfo (`device_info`) — `expr` is a required `{Placeholder}` without `7#`/`8#` — [xeelo-grammar.md](../entities/xeelo-grammar.md#client-userinfo--client-deviceinfo) |
| `defaultValue` | `ObjectDefaultLineValue`, except **`description_memo`**: HTML into `ObjectDefaultLineDescMemo` |

Placeholders compiled at generate time (`id{FIELD}` and `{source.value}`):

- `id{FIELD_CODE}` → `id{ObjectLineID}`
- `{sourceKey.valueKey}` → **`ObjectLineSourceValueBind`** of that source value (not `value`, not the row ID). Numeric bind stays unquoted (`id123 != 2`); any other bind is a STRING with **single quotes** (`id9108 != 'FIO'`). Double quotes are invalid. Full grammar: [xeelo-grammar.md](../entities/xeelo-grammar.md).

**IDs:** `ids.explicit.templates`, `objectDefaultLines` keys `{template}/{field}` when more than one template (single template keeps field-only keys), optional `objectDefaultExternalLinks`.

## Object actions (`spec/object-actions.yaml`)

Optional fragment for **ObjectAction** (server automation on save/workflow). See [entities/object-actions.md](../entities/object-actions.md). Node.js scripts: [entities/nodejs-esm.md](../entities/nodejs-esm.md) — always ESM (`EndPointRunESM: "1"`); mutations on the current request must not refresh (`withRefresh: false`, no `createType`). GraphQL identifiers in `CustomJS` must match **site** `object.code` / field codes from env after extract ([graphql.md](../entities/graphql.md)).

```yaml
objectActions:
  - key: load-transactions
    name: Load transactions
    typeCode: spEndPointRunNodeJSMainLast
    order: 10
    workflowSteps: [Draft]
    params:
      CustomJS: |
        import { XeeloGraphQLClient } from "@xeelo/graphql-client";
        export async function main() { return "OK"; }
      EndPointRunWait: "1"
      EndPointRunESM: "1"
      ApplicableEventType: "Save,SaveNew"
      ResponseTextObjectLineID: { field: RESULT_MEMO }
    conditions:
      - field: LOAD_TX
        type: equals_text
        param1: "1"
```

`params.*.ObjectLineID` values may be `{ field: CODE }` and resolve to the line ID. Condition `type` slugs match update actions.

**IDs:** `objectActions`, `objectActionParams` (`action/paramCode`), `objectActionConditions` (`action/field/type`), `workflowStepObjectActions` (`action/stepName`).

### `source`

```yaml
source:
  transfer: projects/account-object/output/object-transfer.xml
  objectId: 9002
  objectCode: ACCOUNT
  extractedAt: "2026-08-11"
```

### Extract from transfer

```bash
python scripts/extract-object-transfer-to-spec.py \
  projects/account-object/output/object-transfer.xml \
  -o projects/account-object

python scripts/extract-object-transfer-to-spec.py \
  projects/cars/ObjectSetup_20260811_084036.xml \
  --object-id 6097 \
  -o projects/cars
```

After import on site: re-export object from Admin, extract again, commit updated `ids.explicit` (including `roles` / `statuses` maps).

## onGrid

### `onGrid.fields` (by field `code`)

Sets **ObjectLine** display flags for inbox grid:

| Spec key | DB column |
|----------|-----------|
| `allowed` | `ObjectLineOnGridIsAllowed` |
| `name` | `ObjectLineOnGridName` |
| `isTag` | `ObjectLineOnGridIsTag` |
| `isSearch` | `ObjectLineOnGridIsSearch` |

### `onGrid.layouts`

Creates **ObjectLineOnGrid** rows — placement per layout variant:

| Spec key | DB column |
|----------|-----------|
| `size` | `ObjectLineOnGridSize` |
| `type` | `ObjectLineOnGridType` |
| `module` | `ObjectLineOnGridModule` |
| `placements[].row` | `ObjectLineOnGridRow` |
| `placements[].columns[].field` | resolves to `ObjectLineID` |
| `position` | `ObjectLineOnGridPosition` — start column in percent (0–99) |
| `length` | `ObjectLineOnGridLength` — column span in percent (1–100); row columns should sum to 100 |
| `valueWidth` | `ObjectLineOnGridValueWidth` |
| `labelType` | `ObjectLineOnGridLabelType` |

## Generate

```bash
python scripts/generate-object-transfer.py my-spec.yaml \
  -o output/object-transfer.xml \
  --zip output/object-transfer.zip
```

See [object-transfer-format.md](object-transfer-format.md).
