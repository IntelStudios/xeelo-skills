# Xeelo Spec Format (v2)

**Xeelo Spec** is the agent's structured input before generating **Object Transfer** XML. It may be a single YAML file or a **multi-file** directory with an entry `xeelo-spec.yaml` and `includes`.

JSON Schema (merged spec): [`schema/xeelo-spec.schema.json`](../../schema/xeelo-spec.schema.json)

## Multi-file layout (Account)

```
projects/account-object/
  xeelo-spec.yaml       # metadata + includes
  spec/
    object.yaml         # object, objectType, company, layout, onGrid
    references.yaml     # numberedníky (optional)
    lookups.yaml        # dotazovací mapy (optional)
    language-table.yaml # LanguageTable translations (optional)
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
  requestTitleField: TITLE
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
| `object` | yes | Object identity (`name`, `code`, `objectType`, optional `requestTitleField`, `icon`, `color`) |
| `objectType` | no | ObjectType tree visuals (`icon`, `color`). Type **name** stays `object.objectType`. |
| `company` | yes | Company row in transfer (`name`, optional `icon`) |
| `layout.tabs[]` | yes | Tabs with nested sections and fields |
| `onGrid` | no | Inbox grid display + placement (typically in `object.yaml`) |
| `languageTable` | no | Translated labels — [`spec/language-table.yaml`](#localization-speclanguage-tableyaml) |
| `objectMessages` | no | HTML modals — [`spec/object-messages.yaml`](#object-messages-specobject-messagesyaml) |
| `workflow` | no | Defaults to minimal 2-step flow |
| `ids.base` | no | Per-table max PK for **new** rows (`ObjectLine: 9112` → next is 9113). Omit for greenfield (default 9000 per table). Legacy: a single integer is the default for tables not in the map. |
| `ids.explicit` | no | Stable IDs from site / transfer (see below) |
| `ids.byTable` | no | This object's ID inventory from extract |
| `source` | no | Provenance after extract from transfer |
| `transferVersion` | no | `OT_Version` — default `1.3.0` |

Generator **always** creates `Company`, `ObjectType`, `Role`, and `RequestStatus` rows from spec definitions and `ids.explicit`.

## Tree icons and colors

Inbox tree icons and colors sit on the entity that owns them — `object`, `objectType`, and `company` are siblings in `spec/object.yaml`. Do not put ObjectType color on `object`.

```yaml
object:
  name: Account
  objectType: Finance                        # type name (unchanged)
  icon: "fa-university fa-solid fa-fw"       # ObjectTreeIcon
  color: blue                                # ObjectTreeColor = CustomColorCode
objectType:
  icon: "fa-coins fa-solid fa-fw"            # ObjectTypeTreeIcon
  color: blue-steel                          # ObjectTypeTreeColorBack
company:
  name: KB
  icon: "fa-building fa-solid fa-fw"         # CompanyTreeIcon
```

All of `icon` / `color` are optional, max 50 characters. Empty values are omitted from Object Transfer (existing site values stay).

**Icons** are Font Awesome **6.5.1** class strings as Admin stores them: `fa-{id} fa-{variant} fa-fw` (`solid` / `regular` / `light` / `thin` / `brands`). Xeelo User GUI ships 6.5.1 — icons from a newer FA release will not render. When choosing an icon, search the local catalog: `python scripts/search-fa-icons.py --query bank` ([`data/fontawesome-icons.json`](../../data/fontawesome-icons.json)).

**Colors** are `CustomColor.CustomColorCode` (e.g. `blue`), **not** HEX. Seed palette: [`data/enums/CustomColor.json`](../../data/enums/CustomColor.json). Site extras after DB extract: `env/shared/custom-colors.yaml`. The generator writes the code onto Company/Object/ObjectType; it does **not** emit `CustomColor` rows.

| Spec | Column | Live? |
|------|--------|-------|
| `object.icon` | `ObjectTreeIcon` | yes |
| `object.color` | `ObjectTreeColor` | yes (treeview icon color) |
| `objectType.icon` | `ObjectTypeTreeIcon` | yes |
| `objectType.color` | `ObjectTypeTreeColorBack` | yes (Admin “Icon Color”) |
| `company.icon` | `CompanyTreeIcon` | yes |
| — | `ObjectTypeTreeColorFont` | **obsolete** (Admin “Font Color (obsolete)”) — not in spec |
| — | `CompanyTreeColor` | **obsolete** (Admin “Color (obsolete)”) — not in spec |

`ObjectTypeTreeColor` is not a SQL column (stale Admin model only).

## Layout: tabs → sections → fields

Each object can have **multiple tabs** (left/right via `placement`) and **multiple sections** per tab.

### Tab properties

| Property | Maps to |
|----------|---------|
| `name` | `ObjectLineTabName` |
| `placement` | `ObjectLineTabPlacement` (`0` left, `1` right) |
| `order` | `ObjectLineTabOrder` |
| `alwaysHidden` | `ObjectLineTabAlwaysHidden` — hide the whole tab. Common for a tab that only holds helper lines. Not template `hidden: true`. |

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
| `uniqueId` | `ObjectLineUniqueID` (1 Object, 2 Object/Template, 3 Object/Requestor, 4 Object/Template/Requestor). Also sets `ObjectLineIsUnique = 1`. [object-model.md](../entities/object-model.md#unique) |
| `autonumber` | Bind catalog key from `spec/autonumbers.yaml` on this layout field (single default template). Prefer `templates.fields.<code>.autonumber` when `templates.yaml` exists. Text (type 3) only. |
| `descMemoBorder`, `descMemoPadding` | Description memo extras. **`descMemoBorder` defaults to false** (Admin/SQL `0`); omit it or set `false`. Use `true` only when the user wants a visible box. |
| `buttonMessage`, `colorFont`, `colorBack` | Button extras |
| `isReferenceLink` | `ObjectLineIsReferenceLink` (combo types) |
| `alwaysHidden` | `ObjectLineIsHidden` — line never shown in GUI (definition). Distinct from template `hidden: true` / `extended.hidden`. |

`object.requestTitleField` is a **field code** on the object (not a layout extra). It sets `Object.RequestTitleObjectLineID` — that line’s value is the request title in inbox, header, and links.

Combo / radio / multi **require** `reference`. Lookup on the same field is allowed (query map). Do not use lookup instead of a číselník.

## Autonumbers (`spec/autonumbers.yaml`)

Site-wide sequence catalog (`ObjectLineAutoNumber`). Bind on the **template line**, not as a field type — [object-model.md](../entities/object-model.md#autonumber).

```yaml
# spec/autonumbers.yaml
autonumbers:
  request_no:
    description: Request number
    format: REQ####
    next: 1
    # resetTypeId: 1   # optional Yearly
```

```yaml
# layout field (unique is on ObjectLine)
- name: Request number
  code: REQUEST_NO
  type: text
  uniqueId: 1

# spec/templates.yaml (bind + usually not user-edited)
templates:
  - key: default
    isDefault: true
    fields:
      REQUEST_NO:
        autonumber: request_no
        alwaysDisabled: true
```

On a single default template you may set `fields[].autonumber: request_no` instead of `templates.yaml`. Format: one contiguous `#` run (zero-padded number), optional `YYYY` / `YY` / `MM` / `DD`. **IDs:** `ids.explicit.autonumbers`.

## Localization (`spec/language-table.yaml`)

Canonical `name` values stay on the entity (usually English). Translations are a separate map — [localization.md](../entities/localization.md).

```yaml
# spec/language-table.yaml
languageTable:
  object:
    cs: Účet
  tabs:
    General:
      cs: Obecné
  sections:
    General/Details:
      cs: Podrobnosti
  lines:
    ACCOUNT_NUMBER:
      cs: Číslo účtu
  templateHints:
    default:
      ACCOUNT_NUMBER:
        cs: Zadejte IBAN bez mezer
```

Generator emits `LanguageTable` rows and parent→`LanguageTable` ObjectSetup edges. Extract writes this fragment only when translations exist. After `/publish` (or `/precompile` if the OT is already applied) so User GUI picks up labels.

Do not put Czech (or other languages) into `object.yaml` `name` fields. Site rules (always `cs`, onGrid stays English): `projects/<name>/conventions.md`.

## References (`spec/references.yaml`)

Top-level `references` map defines greenfield číselníky (`ObjectLineSource`). Fields use `reference.referenceId` (site ID) or `reference.reference` (key).

| Režim | `references` shape | Emit |
|-------|-------------------|------|
| system | (none — only `reference.referenceId`) | FK on ObjectLine only |
| fixed values | `references.{key}.values[]` | ObjectLineSource + ObjectLineSourceValue |
| refObject | `references.{key}.refObject` | ObjectLineSource + ObjectLineSourceRefObject |

New `references.*` default **`styleId: 4`** (Value / `ObjectLineSourceStyleID`). Explicit `styleId` in spec wins. System lists (`reference.referenceId`) are not restyled.

```yaml
# spec/references.yaml
references:
  colors:
    name: Colors
    typeId: 1
    styleId: 4
    values:
      - { value: "1", label: Red }

# field:
reference:
  reference: colors
  filterField: COMPANY           # optional — ObjectLineSourceFilterObjectLineID
# or site system list:
reference:
  referenceId: 1
```

refObject picker (values from another object’s requests):

```yaml
references:
  payment_label:
    name: Payment label
    typeId: 1
    styleId: 1
    refObject:
      objectId: 9102
      requestType: all
      lines:
        value: line_label_id
        valueName: line_name
        valueBind: line_label_id
        valueFilter: line_applicability   # compared to consuming filterField
```

| Spec | Column |
|------|--------|
| `reference.filterField` | `ObjectLineSourceFilterObjectLineID` — line **on this object** |
| `values[].filter` | `ObjectLineSourceValueFilter` — comma-split list vs filter field (fixed values) |
| `refObject.lines.valueFilter` | `ValueFilterObjectLineID` — line **on the referenced object**; option shown when it equals the filter field |

Load still accepts `sources:` / `reference.source` / `sourceId`. Extract writes `references` / `reference.reference`.

See [`recipes/add-reference-field.md`](../../recipes/add-reference-field.md).

## Lookups (`spec/lookups.yaml`)

Top-level `lookups` map is the query-map definition (name, match, values). The field only binds: which map, which Source field, optional Filter field.

```yaml
# spec/lookups.yaml
lookups:
  priority_by_kind:
    name: Priority by kind
    matchId: 1
    values:
      - { source: demo, return: LOW }
      - { source: full, return: HIGH }

# field (combo still needs a reference whose binds include LOW/HIGH):
reference:
  reference: ks_priority
lookup:
  lookup: priority_by_kind
  sourceField: ks_kind
  filterField: ks_flag          # optional
```

| Spec | Column |
|------|--------|
| `values[].source` | `ObjectLineLookupSourceValue` — match the Source field value |
| `values[].return` | `ObjectLineLookupReturnValue` — written to this field |
| `values[].filter` | `ObjectLineLookupFilterValue` — **exact** `==` vs Filter field (omit / null when unused) |
| `values[].sourceTo` | `ObjectLineLookupSourceValue1` — range end when `matchId: 2` |
| `sourceField` | `ObjectDefaultLineLookupObjectLineID` (required) |
| `filterField` | `ObjectDefaultLineLookupFilterObjectLineID` |

`source` is the match key, not a combo label. Combo labels come from the **reference**.

Inline `lookup.values` on the field still works (one-off map). Same key in `lookups:` = one `ObjectLineLookup` shared by fields.

See [`recipes/add-lookup-field.md`](../../recipes/add-lookup-field.md).

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
    references:
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
      Large/Grid/Items/ACCOUNT_NUMBER: 9024
      Small/Grid/Items/ACCOUNT_NUMBER: 9025
```

Key is `{size}/{type}/{module}/{field code}`. Older specs that keyed only by field code still work for the **first** layout that uses that field.

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

`workflow.steps[].name` is the display label (`WorkflowStepName`) and is **not** unique. When two steps share a name, extract emits `key` (`added_by_system_3698`) and `ids.explicit.workflowSteps` maps that key. Generate uses `step.key` or `step.name`. Same for `steps[].actions[].key` when button names collide. Unique names (`Draft`) stay as today — no `key` field.

```yaml
- key: added_by_system_3698
  name: Added by system
  role: requestor
  status: saved
```

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

Condition `type` slugs match platform seed (`contains`, `equals_text`, `is_empty`, …). Extract omits access rows at **refresh** defaults (editable=0, visible=1). List `editable: true` for fields the user must change on the update form; `visible: false` to hide. `editable: true` implies visible. Optional `access[].sublineId` for a subgrid column.

**Not in spec v1:** `ObjectUpdateActionUserList` (User admin only).

## Object messages (`spec/object-messages.yaml`)

Optional fragment for **ObjectMessage** (HTML modal). See [entities/object-messages.md](../entities/object-messages.md). Attach to an update action with `updateActions[].messages`.

```yaml
# xeelo-spec.yaml
includes:
  - spec/object.yaml
  - spec/object-messages.yaml
  - spec/update-actions.yaml
  - spec/language-table.yaml
  - spec/ids.yaml
```

```yaml
objectMessages:
  - key: retag_payments
    name: Retag payments
    style: warning          # information | warning | error
    order: 10
    html: |
      <p>Saving this label will retag all payments that currently have it assigned.</p>
    # conditions:            # optional; same slugs as update-action conditions
    #   - field: NAME
    #     type: is_not_empty
```

```yaml
languageTable:
  objectMessages:
    retag_payments:
      cs: Přestítkovat platby
      html:
        cs: <p>Uložením tohoto štítku se přestítkují všechny platby, které ho mají přiřazený.</p>
```

**IDs:** `ids.explicit.objectMessages`, `objectMessageConditions` (`{key}/{field}/{type}`), plus `objectUpdateMessages` on the update-action link.

Canonical HTML is English on `html:` (OT column `ObjectMessageFromat`). Translations use LanguageTable ColumnName `ObjectMessageFormat`. Style **Error** disables Continue on the new/update form; **Warning** lets the user Cancel or Continue.

## Templates (`spec/templates.yaml`)

Optional fragment for multiple **ObjectDefault** rows. Omit it to keep a single default template (current behaviour; field `mandatory` applies there).

```yaml
templates:
  - key: cash_register
    name: Cash register
    isDefault: true
    fields:
      TYPE: { hidden: true }
    access:
      - field: SECRET
        visible: false
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
| `alwaysDisabled: true` | `ObjectDefaultLineIsDisabled = 1` (Admin Always disabled). Distinct from `extended.disabled` |
| `mandatory: true` | `ObjectDefaultLineValidationID = 1` (unless extended is also set) |
| *(neither `mandatory` nor `extended`)* | `ObjectDefaultLineValidationID = 2` (Optional) — always written; omitting the column is `NULL` and Admin autosaves |
| `extended.hidden/disabled/mandatory` | Independent boolean `condition` expressions (no `v#` prefix) — [xeelo-grammar.md](../entities/xeelo-grammar.md#extended-validation) |
| `access[]` | **ObjectDefaultAccess** create-form visible/editable. Refresh seeds **both true**; list only hide/lock exceptions. Same `{field, editable, visible, sublineId?}` shape as `workflow.steps[].access` and `updateActions[].access`. Not `hidden` / `alwaysDisabled`. |
| `clientCalculation.type` / `expr` | Client-Math (`math`) / Client-String (`string`) — stored **without** `1#`/`2#` — [xeelo-grammar.md](../entities/xeelo-grammar.md#client-math-vs-client-string). Client-UserInfo (`user_info`) / Client-DeviceInfo (`device_info`) — `expr` is a required `{Placeholder}` without `7#`/`8#` — [xeelo-grammar.md](../entities/xeelo-grammar.md#client-userinfo--client-deviceinfo) |
| `defaultValue` | `ObjectDefaultLineValue`, except **`description_memo`**: HTML into `ObjectDefaultLineDescMemo` |
| `hint` | `ObjectDefaultLineHint` — runtime field hint (plain or HTML). All types except `empty_space`. Canonical English; translations in `languageTable.templateHints.<templateKey>.<code>`. Not `defaultValue` on description memo. |
| `autonumber` | Catalog key from `spec/autonumbers.yaml` → `ObjectDefaultLineAutoNumberID`. Text (3) only. Mutually exclusive with input mask. |

Placeholders compiled at generate time (`id{FIELD}` and `{source.value}`):

- `id{FIELD_CODE}` → `id{ObjectLineID}`
- `{sourceKey.valueKey}` → **`ObjectLineSourceValueBind`** of that source value (not `value`, not the row ID). Numeric bind stays unquoted (`id123 != 2`); any other bind is a STRING with **single quotes** (`id9108 != 'FIO'`). Double quotes are invalid. Full grammar: [xeelo-grammar.md](../entities/xeelo-grammar.md).

**IDs:** `ids.explicit.templates`, `objectDefaultLines` keys `{template}/{field}` when more than one template (single template keeps field-only keys; generator also accepts `{template}/{field}` from extract). Optional `objectDefaultAccess` (`{template}/{field}` or field-only when a single template), optional `objectDefaultExternalLinks`.

## Object actions (`spec/object-actions.yaml`)

Optional fragment for **ObjectAction** (server automation on save/workflow). See [entities/object-actions.md](../entities/object-actions.md). Node.js scripts: [entities/nodejs-esm.md](../entities/nodejs-esm.md) — always ESM (`EndPointRunESM: "1"`); mutations on the current request must not refresh (`withRefresh: false`, no `createType`). GraphQL identifiers in `CustomJS` must match **site** `object.code` / field codes from env after extract ([graphql.md](../entities/graphql.md)). New lines often land as `line_{ObjectLineID}_{slug}` even if the spec used a shorter `code`.

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
| `isTag` | `ObjectLineOnGridIsTag` — **only** `text` / `textarea` (types 3, 4). Field values become request-grid tag filters (AND). See [object-line-types.md](../entities/object-line-types.md#on-grid-tag). |
| `isSearch` | `ObjectLineOnGridIsSearch` — typed search; types 3, 4, 8, 12 |

```yaml
onGrid:
  fields:
    CATEGORY:
      allowed: true
      isTag: true
```

`CATEGORY` must be `type: text` or `textarea`. Extract emits `onGrid.fields` when `allowed`, `isTag`, or `isSearch` is set (tag-only helpers: `allowed: false`, `isTag: true`). After deploy, **/publish** so the tag cache SQL is rebuilt.

Inbox cells parse `[badge:{CustomColorCode}_{text}]` as a colored chip (`.xe-badge-{code}`). Do **not** store badge tokens on an `isTag` line — use a separate display text line (`isTag: false`). Combo cannot be `isTag`. See [object-line-types.md](../entities/object-line-types.md#on-grid-badge).

### `onGrid.layouts`

Creates **ObjectLineOnGrid** rows — placement per layout variant. A variant is **`size` + `type`** (`Grid` / `Table`) + `module`. The same field may appear in several layouts; each variant is its own row (`ids.explicit.objectLineOnGrid` key `{size}/{type}/{module}/{code}`).

| Spec key | DB column |
|----------|-----------|
| `size` | `ObjectLineOnGridSize` — `Small` (mobile), `Medium` (tablet), `Large` (desktop) |
| `type` | `ObjectLineOnGridType` — `Grid` or `Table` |
| `module` | `ObjectLineOnGridModule` — `Items` or `Tasks` |
| `placements[].row` | `ObjectLineOnGridRow` — `T`, `A`–`E` (spec “pseudo-rows”; see Grid vs Table) |
| `placements[].columns[].field` | resolves to `ObjectLineID` |
| `position` | `ObjectLineOnGridPosition` — start column in percent (0–99) |
| `length` | `ObjectLineOnGridLength` — column span in percent (1–100); row columns should sum to 100 |
| `valueWidth` | `ObjectLineOnGridValueWidth` — percent of the cell for the **value**. `0` = auto. **`100` + Horizontal = hide the column label** (Admin ValueWidthLabelHidden). |
| `labelType` | `ObjectLineOnGridLabelType` — **1 Horizontal** (default), **2 Vertical**. SQL also has `0` None; Admin does not offer it — do not spec `0`. |

Omit a size to keep the platform default for that breakpoint. Add `Small` when the inbox on a phone should show fewer columns than desktop `Large`.

To show chips without a column title on **Grid**, set `labelType: 1` and `valueWidth: 100`.

**Grid vs Table**

| `type` | How `placements[].row` renders |
|--------|--------------------------------|
| **Grid** | Each letter (`T`, `A`–`E`) is a visual row; cards wrap/stack. |
| **Table** | Always **one** visual row. Pseudo-rows from the spec **do not wrap** — columns stay on a single line and the table **scrolls horizontally**. |

Use **Grid** when the inbox card should stack (typical mobile `Small`). Use **Table** when the inbox is a spreadsheet-like list and overflow should scroll right, not wrap.

## Generate

```bash
python scripts/generate-object-transfer.py my-spec.yaml \
  -o output/object-transfer.xml \
  --zip output/object-transfer.zip
```

See [object-transfer-format.md](object-transfer-format.md).
