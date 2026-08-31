# Xeelo Spec Format (v2)

**Xeelo Spec** is the agent's structured input before generating **Object Transfer** JSON. It may be a single YAML file or a **multi-file** directory with an entry `xeelo-spec.yaml` and `includes`.

JSON Schema (merged spec): [`schema/xeelo-spec.schema.json`](../../schema/xeelo-spec.schema.json)

## Multi-file layout (Account)

```
projects/<name>/
  xeelo-spec.yaml       # metadata + includes
  spec/
    object.yaml         # object, objectType, company, layout, onGrid
    references.yaml     # numberedníky (optional)
    lookups.yaml        # dotazovací mapy (optional)
    autonumbers.yaml    # sequences (optional)
    object-services.yaml # ObjectService catalog (optional)
    language-table.yaml # LanguageTable translations (optional)
    comments.yaml       # TableComments HTML notes (optional)
    workflow.yaml       # roles, statuses, workflow
    templates.yaml      # ObjectDefault (optional)
    object-actions.yaml # ObjectAction (optional)
    object-messages.yaml
    update-actions.yaml
    periodics.yaml
    notifications.yaml  # email templates (optional)
    subgrids.yaml       # ObjectSub trees (optional)
    ids.yaml            # ids
```

**Entry** `xeelo-spec.yaml`:

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
              width: 50
              order: 1
              slot: 1
              mandatory: true
onGrid:
  fields:
    ACCOUNT_NUMBER:
      allowed: true
      name: Account No
  layouts: [...]
```

Generator and extract use [`scripts/ot_builder/spec_loader.py`](../../scripts/ot_builder/spec_loader.py) — `load_spec(path)` accepts a file or directory; monolithic YAML without `includes` still works.

## YAML key order

Extract writes spec YAML with PyYAML `sort_keys=False`, so mapping key order is the insertion order in [`scripts/ot_builder/extract.py`](../../scripts/ot_builder/extract.py). `write_spec` and [`scripts/normalize-spec-yaml.py`](../../scripts/normalize-spec-yaml.py) re-apply the same order from [`scripts/ot_builder/spec_key_order.py`](../../scripts/ot_builder/spec_key_order.py). If the agent writes keys in a different order, the next extract (or normalize) reshuffles the mapping and git shows a noisy diff.

Rules:

- **New mapping:** emit keys in extract order. Skip omitted optionals; put the next present key in its canonical slot (not at the end). New layout fields always include `width` and `order` (extract always writes them); tabs always include `placement` and `order`; sections always include `order` and `width`.
- **Edit:** insert a new key at the canonical position among keys that are already present. Do not rewrite the rest of the file just to tidy order — run normalize after the edit.
- **Omit** defaults extract omits (`matchId: 1`, `isActive: true`, `descMemoBorder: false`).
- After editing a change-loop spec: `python scripts/normalize-spec-yaml.py projects/<name>/changes/<slug>/objects/<object>/`.

Layout field order (skip keys that do not apply): `name`, `code`, `type`, `width`, `order`, `slot`, `precision`, `objectSub` / `objectSubId`, `saveAction`, `uniqueId`, type extras, `alwaysHidden`, `isActive`, `mandatory` (layout only when there is no `templates.yaml`), `reference`, `lookup`, `autonumber`. Full tuples: [`spec_key_order.py`](../../scripts/ot_builder/spec_key_order.py).

## Top-level fields

| Field | Required | Description |
|-------|----------|-------------|
| `version` | yes | Must be `2` |
| `kind` | yes | `create_object` |
| `transferType` | no | `object` (default) |
| `object` | yes | Object identity (`name`, `code`, `objectType`, optional `icon`, `color`, `requestTitleField`, `gridSort`) |
| `objectType` | no | ObjectType tree visuals (`icon`, `color`). Type **name** stays `object.objectType`. |
| `company` | yes | Company row in transfer (`name`, optional `icon`) |
| `layout.tabs[]` | yes | Tabs with nested sections and fields |
| `onGrid` | no | Inbox grid flags + placement (`object.yaml`). Catalog and new-object default: [ongrid.md](../entities/ongrid.md) |
| `autonumbers` | no | Sequences — [`spec/autonumbers.yaml`](#autonumbers-specautonumbersyaml) |
| `objectServices` | no | External ObjectService catalog — [`spec/object-services.yaml`](#object-services-specobject-servicesyaml) |
| `subgrids` | no | ObjectSub trees — [`spec/subgrids.yaml`](#subgrids-specsubgridsyaml) |
| `languageTable` | no | Translated labels — [`spec/language-table.yaml`](#localization-speclanguage-tableyaml) |
| `comments` | no | Admin HTML comments — [`spec/comments.yaml`](#admin-comments-speccommentsyaml) |
| `objectMessages` | no | HTML modals — [`spec/object-messages.yaml`](#object-messages-specobject-messagesyaml) |
| `notifications` | no | Email templates — [`spec/notifications.yaml`](#notifications-specnotificationsyaml) |
| `workflow` | no | Defaults to minimal 2-step flow |
| `ids.base` | no | Per-table max PK for **new** rows (`ObjectLine: 9112` → next is 9113). Omit for greenfield (default 9000 per table). Legacy: a single integer is the default for tables not in the map. |
| `ids.explicit` | no | Stable IDs from site / transfer (see below) |
| `ids.byTable` | no | This object's ID inventory from extract |
| `transferVersion` | no | `OT_Version` — default `1.3.0` |

Generator diffs against the latest DB-transfer snapshot. It **omits** any row whose Orig. ID already exists unchanged, including `Company` / `ObjectType` / `Role` / `RequestStatus` / `Workflow` when this package only references them. Recycled workflow also uses `workflow.reuse: true` so the shared process definition is not generated.

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
| `sections` | Nested sections (YAML after `order`; extract writes `alwaysHidden` after this list) |
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
| `width` | `ObjectLineTypeWidth` — field width in **percent** (1–100) |
| `order` | `ObjectLineOrder` |
| `slot` | `ObjectLineSlot` (unique per object; not required for types 5, 6, 13, 16, 17) |
| `precision` | `ObjectLineNumberPrecision` / `ObjectSubLineNumberPrecision` (number fields). **Required** on subgrid numbers — omit it and values do not store |
| `objectSub` | Spec key in `subgrids:` → emit `ObjectSub` tree and set `ObjectLine.ObjectSubID` |
| `objectSubId` | Existing/shared `ObjectSub` Orig. ID (no tree emit). Type 5. Prefer `objectSub` for new trees |
| `saveAction` | `ObjectLineButtonSaveAction` (button fields): **0 Save** (stay on the request), **1 Save & close**. Enum: [`ObjectLineButtonSaveAction.json`](../../data/enums/ObjectLineButtonSaveAction.json) |
| `uniqueId` | `ObjectLineUniqueID` (1 Object, 2 Object/Template, 3 Object/Requestor, 4 Object/Template/Requestor). Also sets `ObjectLineIsUnique = 1`. [object-model.md](../entities/object-model.md#unique) |
| `numberSeparator` / `numberMin` / `numberMax` | Number extras |
| `textInputType` | `ObjectLineTextInputType` (0 Default, 1 Bar Code, 2 Location) |
| `columnNumbers` | `ObjectLineNumberColumns` (radio / multi) |
| `webFrameTypeId` | `WebFrameTypeID` (1–4) |
| `height` | `ObjectLineHeight` (memo, report) — **pixels**. Omit or `0` = unlimited. |
| `descMemoBorder`, `descMemoPadding` | Description memo extras. **`descMemoBorder` defaults to false** (Admin/SQL `0`); omit it or set `false`. Use `true` only when the user wants a visible box. |
| `buttonMessage` | Confirm text before the click saves (`ObjectLineButtonMessage`) |
| `colorFont` | Button **text** — `CustomColor.CustomColorCode` (e.g. `white`). Admin Color Font. GUI: `xe-font-{code}` |
| `colorBack` | Button **background** — same palette (e.g. `blue`). Admin Color Back. GUI: `xe-back-{code}` |
| `isReferenceLink` | `ObjectLineIsReferenceLink` (combo types) |
| `attachmentStorageId`, `ocr`, `ocrLang`, `imageResizeMax`, `mobileScan`, `mobileSignature` | Attachment extras |
| `previewField`, `previewDownload` | Attachment preview (`previewField` = attachment field **code**) |
| `alwaysHidden` | `ObjectLineIsHidden` — line never shown in GUI (definition). Distinct from template `hidden: true` / `extended.hidden`. |
| `isActive` | `ObjectLine.IsActive`. `false` soft-disables the line (OT does not delete). Omit the field from spec and the site row stays **active**. |
| `mandatory` | `ObjectDefaultLineValidationID = 1` (default template unless overridden in `templates`). Omit `mandatory`/`extended` → still emit **`ValidationID = 2`** (Optional); do not leave the column unset |
| `reference` | `ObjectLineSource` on **ObjectLine** (číselník) — combo, radio, multi |
| `lookup` | `ObjectLineLookup` on **template line** (dotazovací mapa) |
| `autonumber` | Bind catalog key from `spec/autonumbers.yaml` on this layout field (single default template). Prefer `templates.fields.<code>.autonumber` when `templates.yaml` exists. Text (type 3) only. |

`object.requestTitleField` is a **field code** on the object (not a layout extra). It sets `Object.RequestTitleObjectLineID` — that line’s value is the request title in inbox, header, and links.

`object.gridSort` is default inbox sort (Admin Object → Sorting), not a template setting:

```yaml
object:
  gridSort:
    field: DATE        # field code → ObjectGridSortObjectLineID
    type: DESC         # ASC | DESC → ObjectGridSortType
```

Omit the block when there is no default line sort. After deploy, **/publish** so the sort cache SQL is rebuilt. A user filter can override. See [object-model.md](../entities/object-model.md).

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
        alwaysDisabled: true
        autonumber: request_no
```

On a single default template you may set `fields[].autonumber: request_no` instead of `templates.yaml`. Format: one contiguous `#` run (zero-padded number), optional `YYYY` / `YY` / `MM` / `DD`. **IDs:** `ids.explicit.autonumbers`.

## Object services (`spec/object-services.yaml`)

Site catalog of **External service** (type 1) URLs. Bind on the **template line** via Client-Service — [object-services.md](../entities/object-services.md). Recipe: [add-client-service.md](../../recipes/add-client-service.md).

```yaml
# spec/object-services.yaml
objectServices:
  ares_name:
    name: ARES Name
    type: external          # ObjectServiceTypeID 1; default; only type in spec
    link: "https://<ares-host>/api/parse?query={@1}&field=Name"
```

```yaml
# spec/templates.yaml
templates:
  - key: default
    isDefault: true
    fields:
      COMPANY_NAME:
        clientCalculation:
          type: service
          service: ares_name
          expr: "id{ICO}"
```

`link` keeps `{@1}`…`{@n}` as-is (runtime). `expr` `id{CODE}` compiles like other client calcs. One service row per target field (typically `&field=`). **IDs:** `ids.explicit.objectServices`.

## Subgrids (`spec/subgrids.yaml`)

ObjectSub tree bound from a parent **type 5** line. Semantics: [object-model.md](../entities/object-model.md#subgrid). Recipe: [add-subgrid.md](../../recipes/add-subgrid.md).

```yaml
# spec/subgrids.yaml
subgrids:
  invoice_lines:
    name: Invoice lines
    width: 80
    layout:
      tabs:
        - name: General
          sections:
            - name: Details
              fields:
                - name: Description
                  code: DESC
                  type: text
                  width: 100
                  order: 1
                  slot: 1
                - name: Qty
                  code: QTY
                  type: number
                  width: 100
                  order: 2
                  slot: 2
                  precision: 0
                - name: Amount
                  code: AMOUNT
                  type: number
                  width: 100
                  order: 3
                  slot: 3
                  precision: 2
    code: invoice_lines
    templates:
      - key: default
        isDefault: true
        fields:
          DESC:
            mandatory: true
            # hint: Line description
            # autonumber: line_no   # same catalog as spec/autonumbers.yaml; text only
          TOTAL:
            alwaysDisabled: true
            clientCalculation:
              type: math
              expr: id{QTY} * id{AMOUNT}   # compiles to ObjectSubLineID
    onGrid:
      fields:
        DESC:
          allowed: true
          isSearch: true
      layouts:
      - size: Large
        type: Grid
        module: Items
        placements:
        - row: T
          columns:
          - field: DESC
            position: 0
            length: 100
            valueWidth: 0
            labelType: 1
```

Parent line + which subgrid template new rows use:

```yaml
# layout
- name: Lines
  code: LINES
  type: subgrid
  objectSub: invoice_lines

# spec/templates.yaml
templates:
  - key: default
    isDefault: true
    fields:
      LINES:
        subgridTemplate: default   # ObjectDefaultLine.ObjectSubDefaultID
    access:
      - field: LINES               # ObjectDefaultAccess — required for a new type-5 line
        visible: true
        editable: true
```

Also emit `workflow.steps[].access` for the parent line on every step that should show the grid. Missing access row = hidden. Recipe: [add-subgrid.md](../../recipes/add-subgrid.md#access).

| Spec | Maps to |
|------|---------|
| `subgrids.<key>` | `ObjectSub` (`ObjectSubName`, optional `ObjectSubCode`, `ObjectSubWidth` — add/edit-row **modal** width %; default **80**, Admin 50–100). Extra fields → extra tabs/sections or stacked `width: 100`, not a wider modal. |
| `layout.tabs/sections/fields` | `ObjectSubLineTab` / `ObjectSubLineSection` / `ObjectSubLine`. Same type slugs and **same extras** as ObjectLine (`precision`, `reference`, … → `ObjectSubLine*`). Not 5 / 13 / 18. |
| `templates[]` | `ObjectSubDefault` + `ObjectSubDefaultLine`. Omit → one Default template, all lines Optional |
| `templates[].fields.*.mandatory` / `hint` / `autonumber` / `alwaysDisabled` / `clientCalculation` / `defaultValue` / `defaultFilter` / `calcDelay` / `calcConfirm` | `ObjectSubDefaultLine*` (lookup is on the **layout** field like ObjectLine: `lookup` + `sourceField` → `ObjectSubDefaultLineLookupID` / `LookupObjectSubLineID`). `id{CODE}` in calc compiles to `ObjectSubLineID`. Client types 1–5 and 7 (no `focus` / `device_info`). Client-Service: `service` key + `ObjectServiceID` (types 1–2 on columns) — [object-services.md](../entities/object-services.md). `defaultValue` → `ObjectSubDefaultLineValue` (or `DescMemo` on `description_memo`). `calcDelay` / `calcConfirm` on the **source** column; omit unless the user asks — [object-line-types.md](../entities/object-line-types.md#client-calc-delay-and-confirm) |
| `onGrid.fields.<code>` | `ObjectSubLine` flags: `allowed` → `ObjectSubLineOnGridIsAllowed`; `isTag` → `ObjectSubLineOnGridIsTag`; `isSearch` → `ObjectSubLineIsSearch`; `isTotal` → `ObjectSubLineIsTotal` (types **3 and 12**) |
| `onGrid.layouts[]` | `ObjectSubLineOnGrid` placement (`size` × Grid/Table × `module`). Same shape as request inbox onGrid, but **`field` only** — no `systemLine` |
| `fields[].objectSub` | Emit the tree (if present) and set `ObjectLine.ObjectSubID` |
| `fields[].objectSubId` | Bind an **existing/shared** `ObjectSub` — generator does **not** emit `ObjectSub*` |
| `templates.fields.<parent>.subgridTemplate` | Parent `ObjectDefaultLine.ObjectSubDefaultID` (requires `objectSub:` key) |

**IDs:** `ids.explicit.subgrids`, `subgridTabs` (`{sub}/{tab}`), `subgridSections` (`{sub}/{tab}/{section}`), `subgridFields` (`{sub}/{code}`), `subgridTemplates` (`{sub}/{template}`), `subgridDefaultLines` (`{sub}/{template}/{code}`), `subgridOnGrid` (`{sub}/{size}/{type}/{module}/{code}`).

Always emit `onGrid` when adding a subgrid (same habit as request inbox `onGrid`): `fields` so columns are allowed on the table, `layouts` for placement. Without `allowed`, the add-row modal still has fields but the **subgrid table** has no columns.

Column extras match ObjectLine ([object-line-types.md](../entities/object-line-types.md#subgrid-columns-objectsubline)): combo/radio/multi **`reference`**, number **`precision`**, attachment `attachmentStorageId`, preview `previewField` (subgrid column code), radio/multi `columnNumbers`. Lookup and client-calc use the same spec keys as the request template; `sourceField` / `id{CODE}` resolve **inside this objectSub**. Types **5 / 13 / 18** are not in `ObjectSubLineType` — do not spec them here.

Not emitted yet: unique/gridSort on sublines, Generate + combo Multiselect, `ObjectSubPrefill*`, comments for `ObjectSub*`.

Czech (and other languages): `languageTable.subgrids.<key>.tabs` / `sections` / `lines` / `templateHints` — [localization.md](../entities/localization.md). Inbox/subgrid **onGrid** titles stay English unless the user asks (`lines.<code>.onGrid`).

Share a site `ObjectSub` on a second object with `objectSubId:` only (same Orig. ID). Do not allocate a new tree.

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
  subgrids:
    kitchensink_lines:
      tabs:
        Extra:
          cs: Další
      sections:
        Extra/Kind:
          cs: Druh
      lines:
        KIND:
          cs: Druh
      templateHints:
        default:
          KIND:
            cs: Vyberte druh
```

Generator emits `LanguageTable` rows and parent→`LanguageTable` ObjectSetup edges. Extract writes this fragment only when translations exist. After `/publish` (or `/precompile` if the OT is already applied) so User GUI picks up labels.

Do not put Czech (or other languages) into `object.yaml` `name` fields. Site rules (always `cs`, onGrid stays English): `projects/<name>/conventions.md`. `ObjectSubName` is not in Admin mass-translate. Subgrid onGrid titles stay English unless asked (`subgrids.*.lines.<code>.onGrid`).

## Admin comments (`spec/comments.yaml`)

HTML notes on configuration entities (`TableComments`), not request comments. Same entity keys as `languageTable`. Values are **lists** (append changelog). See [comments.md](../entities/comments.md). Recipe: [add-table-comment.md](../../recipes/add-table-comment.md).

```yaml
# spec/comments.yaml
comments:
  object:
    - html: "<p>FIO accounts that drive payment import.</p>"
  lines:
    TYPE:
      - html: "<p>Payment source. Hourly periodic matches FIO.</p>"
  periodics:
    load_fio_hourly:
      - html: "<p>2026-08-24: hourly scheduler → load_transactions 9016.</p>"
```

Generator emits `TableComments` rows (`UserID=0`, default `userName` `xeelo-skills`) and parent→`TableComments` ObjectSetup edges. Extract writes this fragment only when comments exist. Simple tags: `p`, `ul`/`ol`/`li`, `strong`/`em`, `br`, `a`. Object Transfer upserts by Orig. ID — omitted comments stay on the site.

Whether the agent **writes** these comments is **Generate table comments** in `projects/<name>/conventions.md` (`ask` | `auto`). HTML language is **Comment language** in that file (missing = `en`). New entity → one description; change → append a dated item; unchanged → skip.

**IDs:** `ids.explicit.tableComments` (`TableName:entityKey:index`, e.g. `ObjectLine:TYPE:0`).

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

`refObject.requestType` is Admin **Request Type** on Reference Object (`ObjectLineSourceRefObjectRequestTypeID`). Default `all`. Not the same as request Create/Update (`RequestTypeID` 1/2/3). Enum: [`ObjectLineSourceRefObjectRequestType.json`](../../data/enums/ObjectLineSourceRefObjectRequestType.json).

| ID | Admin | Spec | Options in the combo |
|----|-------|------|----------------------|
| 0 | All | `all` (default) | last version of each request |
| 1 | Only completed | `completed` | last version only when it is completed |
| 2 | Only inprogress | `in-progress` | last version only when it is not completed |

The generator also writes deprecated `ObjectLineSourceRefObjectIsOnlyCompleted` (`1` iff `completed`); runtime uses Request Type.

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

Lookup that **copies a line from another object’s request** (the combo is a refObject picker): `lookups.*.refObject` with `objectId` + `lines.source` / `lines.return`. Generate does **not** emit `ObjectLineLookupRefObject` yet — patch the OT JSON after generate. Extract omits `refObject` and writes `values: []`. Recipe: [`add-lookup-field.md`](../../recipes/add-lookup-field.md#copy-from-another-object-objectlinelookuprefobject).

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
          # reopenOnSave: open-only-assigned  # WorkflowStepActionReopenTypeID; omit = close after this button
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

### `reuse: true` (existing workflow)

Share a site `Workflow` Orig. ID. Spec still lists steps (keys + `access` for this object’s lines). Generate **does not** emit the shared `Workflow` / `WorkflowStep` / `WorkflowStepAction` definition. `ObjectDefault.WorkflowID` and `WorkflowStepAccess` still go out. Unchanged `Company` / `Role` / … rows are omitted the same way as any other table vs download.

```yaml
workflow:
  mode: full
  reuse: true
  name: Temporary - CREATE
  steps:
    - key: added_by_system_10
      name: Added by system
      role: requestor
      status: saved
      access:
        - field: TITLE
          editable: true
```

`ids.explicit.workflowId` / `workflowSteps` must be the live Orig. IDs. Omit `languageTable.workflow` / `roles` / `statuses` / `stepActions` (or they are ignored on generate).

### `minimal`

Implicit Draft → Active with Submit / Complete. Requires `roles` / `statuses` with keys `requestor`, `owner`, `draft`, `active`, `completed` (or omit — generator uses defaults).

### `full`

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

`steps[].access` maps to **WorkflowStepAccess** (editable/visible per line on that step). Site refresh inserts missing rows as visible + **not** editable, but **Object Transfer does not run that refresh**. For a **new** line, emit `access` on every step that should show it (`editable: true` where users edit; `visible: true` on the rest). A missing row means hidden. Extract omits those defaults from the spec access list; it still writes their Orig. IDs into `ids.explicit.workflowStepAccess` so a later generate can flip editable without minting a duplicate. Admin UI groups this by request status name (e.g. Open).

`steps[].suppressSave: true` → `WorkflowStepIsSuppressSave`. Hides the request **Save** control (`showSaveBtn`). ObjectLine **Button** lines still save. Extract writes the flag only when true.

`steps[].actions[].reopenOnSave` → `WorkflowStepActionReopenTypeID`. Same slugs as template `reopenOnSave`. Applies after that **workflow button**; omit/`none` = close.

Bind email templates by **key** (not Orig. ID). See [notifications](#notifications-specnotificationsyaml).

- `workflow.notification` / `exportFailNotification` / `recallNotification` / `failNotification`
- `steps[].actions[].notification`
- `steps[].notifications: [key]` → `WorkflowStepNotification`

`workflow.reuse: true` does not upsert Workflow / step / action rows, so header and action FKs on a shared process are not changed. Step junction rows can still be emitted.

`steps[].isActive: false` / `steps[].actions[].isActive: false` → `IsActive = 0`. Object Transfer does not delete leftover steps or footer buttons; omit them from spec and the site row stays **active**.

An extra step stays **active** only if `spRefreshWorkflowStep` sees its `(role, status)` as the workflow header, a fail/recall target, or a **`WorkflowStepAction` target**. Change-role ObjectActions alone do not count — omit the targeting step action and the site stores the step with `IsActive = 0`.

**IDs:** `ids.explicit.workflowStepAccess` keys `{stepName}/{field}` or `{stepName}/{field}/sub{sublineId}`. After the first site refresh, reuse the existing `WorkflowStepAccessID` for the same (step, `ObjectLineID`, `ObjectSubLineID`) — do not allocate a new Orig. ID or the unique index will fail. Extract records those IDs even for default (visible, not editable) rows. `ObjectSubLineID` null is the parent type-5 widget; set `access[].sublineId` for a subgrid column.

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
    # reopenOnSave: open-only-assigned   # ObjectUpdateActionReopenTypeID; omit = close after update-version save
    # isActive: false   # soft-delete; omit the action and the site row stays active
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

Condition `type` slugs match platform seed (`contains`, `equals_text`, `is_empty`, …). Do not use `is_not_empty` on **memo** to test the HTML body — the slot is the memo record ID ([object-actions.md](../entities/object-actions.md#objectactioncondition)). Extract omits access rows at **refresh** defaults (editable=0, visible=1). List `editable: true` for fields the user must change on the update form; `visible: false` to hide. `editable: true` implies visible. Optional `access[].sublineId` for a subgrid column.

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

## Notifications (`spec/notifications.yaml`)

Optional fragment for **Notification** (email template). See [entities/notifications.md](../entities/notifications.md). A template has **no `ObjectID`**; Object Transfer pulls it in as a child of Workflow / WorkflowStepAction / WorkflowStepNotification / ObjectAction / PeriodicAction. Every `notifications[].key` must be bound from at least one of those (unbound = generate error).

```yaml
# xeelo-spec.yaml
includes:
  - spec/object.yaml
  - spec/workflow.yaml
  - spec/notifications.yaml
  - spec/object-actions.yaml
  - spec/ids.yaml
```

```yaml
notifications:
  - key: assigned
    name: Assigned to role
    type: single          # single=1 | summary=2
    subject: "{ObjectName} {RequestID}"
    format: |
      <p>Request {RequestID}</p>
      <p>{RequestDetails,100}</p>
    sendTo:
      requestor: true
      role: true          # omit / false bits are not emitted
      # requestorManager / roleManager are Cc, not To
    extra:
      to: ops@example.com   # also `{idNNNN}` (raw slot) or `{Variable,code}`
    conditions:
      - field: TYPE
        type: equals_text
        param1: "1"
    attachments:
      - field: INVOICE    # compressed defaults true
```

Bindings (keys, not IDs):

```yaml
workflow:
  mode: full
  notification: assigned
  # exportFailNotification / recallNotification / failNotification
  steps:
    - name: Draft
      notifications: [assigned]
      actions:
        - name: Submit
          notification: assigned
```

ObjectAction / PeriodicAction:

```yaml
params:
  NotificationID1: { notification: assigned }
  # NotificationID2 on summary periodic (spNotificationDataInsertSummary)
```

Placeholders in `subject` / `format` are **not** rewritten (`{id1234}` stays). Use numeric `ObjectLineID` in `{idXXXX}` — `{idAMOUNT}` is not resolved. `{idXXXX}` is formatted (combo **name**, memo **HTML**); `{idXXXXv}` is the raw slot (combo **bind**, memo **record ID**). Memo body: `{idNNNN}` without `v`. Do not use memo `is_not_empty` on `conditions:` — that tests the record ID. Full catalog: [notifications.md](../entities/notifications.md#placeholders).

`sendTo.requestorManager` / `roleManager` are **Cc**. Conditions: OR on the same field, AND across fields. `steps[].notifications` does not set `WorkflowStepNotification.RequestTypeID` (null = Create and Update). Runtime: [notifications.md](../entities/notifications.md#runtime).

**Not in spec v1:** `NotificationPrintout`, `NotificationCalculation`, `NotificationTempCalc`. Subject/body are not `LanguageTable`-localized.

**IDs:** `ids.explicit.notifications`, `notificationConditions` (`{key}/{field}/{type}`), `notificationAttachments` (`{key}/{field}`), `workflowStepNotifications` (`{stepKey}/{notifKey}`). Extract keys come from `NotificationName` (slug).

## Templates (`spec/templates.yaml`)

Optional fragment for multiple **ObjectDefault** rows. Omit it to keep a single default template (current behaviour; field `mandatory` applies there). Extract still writes this fragment for one template when it has field extras, create-access exceptions, or `reopenOnSave`.

```yaml
templates:
  - key: cash_register
    name: Cash register
    isDefault: true
    reopenOnSave: open-only-assigned
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
| `access[]` | **ObjectDefaultAccess** create-form visible/editable. Refresh seeds **both true**, but OT does not run refresh — for a **new** line emit `visible: true` / `editable: true` or create form hides it. After extract, list only hide/lock exceptions. Same `{field, editable, visible, sublineId?}` shape as `workflow.steps[].access` and `updateActions[].access`. Not `hidden` / `alwaysDisabled`. |
| `clientCalculation.type` / `expr` | Client-Math (`math`) / Client-String (`string`) — stored **without** `1#`/`2#` — [xeelo-grammar.md](../entities/xeelo-grammar.md#client-math-vs-client-string). Client-Service (`service`) — `service` key from `spec/object-services.yaml` → `ObjectServiceID`; `expr` is `{@n}` params without `3#` — [object-services.md](../entities/object-services.md). Client-UserInfo (`user_info`) / Client-DeviceInfo (`device_info`) — `expr` is a required `{Placeholder}` without `7#`/`8#` — [xeelo-grammar.md](../entities/xeelo-grammar.md#client-userinfo--client-deviceinfo) |
| *(server calc / calculation order)* | **Not in spec.** After generate, patch `ObjectDefaultLineCalculationTypeID` + `ObjectDefaultLineCalculation` and `ObjectDefaultLineCalculationOrder` on the OT JSON. Type-5 parents and server types **51–100** need an order row or they never run (missing order → **999999999**, skipped at precompile; type-5 missing a row is **C.72**). [object-line-types.md](../entities/object-line-types.md#server-calculations) |
| `defaultValue` | `ObjectDefaultLineValue`, except **`description_memo`**: HTML into `ObjectDefaultLineDescMemo`. Types and when it fills: [object-line-types.md](../entities/object-line-types.md#default-value-and-filter) |
| `defaultFilter` | `ObjectDefaultLineValueFilter` — combo/radio/multi only. Plain string. **Omit unless the user asks** |
| `calcDelay` | `ObjectDefaultLineClientCalcDelay` (ms) on the **source** line. text / textarea / number. **Omit** = runtime 400. **Do not set unless the user asks** — [object-line-types.md](../entities/object-line-types.md#client-calc-delay-and-confirm) |
| `calcConfirm` | `ObjectDefaultLineIsClientCalcConfirm` — Refresh on text/number source. **Omit** = off. **Do not set unless the user asks** |
| `hint` | `ObjectDefaultLineHint` — runtime field hint (plain or HTML). All types except `empty_space`. Canonical English; translations in `languageTable.templateHints.<templateKey>.<code>`. Not `defaultValue` on description memo. |
| `autonumber` | Catalog key from `spec/autonumbers.yaml` → `ObjectDefaultLineAutoNumberID`. Text (3) only. Mutually exclusive with input mask. |
| `subgridTemplate` | Key of `subgrids.<key>.templates[]` → `ObjectDefaultLine.ObjectSubDefaultID`. Parent field must be `type: subgrid` with `objectSub:`. |
| `reopenOnSave` | `ObjectDefaultReopenTypeID` — omit / `none` / `close` = NULL (request **closes** after create save). `open-only-everytime` (1), `open-with-actions` (2), `open-only-assigned` (3). Same slugs on `updateActions[].reopenOnSave` and `workflow.steps[].actions[].reopenOnSave`. Template/update-action values apply on **new** requests; already-saved requests always stay Open only (everytime). Workflow-button value applies after that transition. Catalog: [`ReopenActionType.json`](../data/enums/ReopenActionType.json). |

Placeholders compiled at generate time (`id{FIELD}` and `{source.value}`):

- `id{FIELD_CODE}` → `id{ObjectLineID}`
- `{sourceKey.valueKey}` → **`ObjectLineSourceValueBind`** of that source value (not `value`, not the row ID). Numeric bind stays unquoted (`id123 != 2`); any other bind is a STRING with **single quotes** (`id9108 != 'FIO'`). Double quotes are invalid. Full grammar: [xeelo-grammar.md](../entities/xeelo-grammar.md).

**IDs:** `ids.explicit.templates`, `objectDefaultLines`, `objectDefaultAccess`. Extract writes **short** field-only keys (`NAME: 18`) when the object has **one** template — not a platform-legacy format. With **two or more** templates the keys are `{template}/{field}` (`default/NAME`, `prefilled/NAME`). A new template always gets **new** Orig. IDs. Field-only keys from a one-template extract belong to the **default** template only; generate must not reuse them for another template (Object Transfer upserts by Orig. ID). Optional `objectDefaultExternalLinks`.

## Object actions (`spec/object-actions.yaml`)

Optional fragment for **ObjectAction** (server automation on save/workflow). See [entities/object-actions.md](../entities/object-actions.md). Node.js scripts: [entities/nodejs.md](../entities/nodejs.md) — always ESM (`export async function main()`); mutations on the current request must not refresh (`withRefresh: false`, no `createType`). GraphQL identifiers in `CustomJS` must match **site** `object.code` / field codes from env after extract ([graphql.md](../entities/graphql.md)). New lines often land as `line_{ObjectLineID}_{slug}` even if the spec used a shorter `code`.

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
      ApplicableEventType: "Save,SaveNew"
      ResponseTextObjectLineID: { field: RESULT_MEMO }
    conditions:
      - field: LOAD_TX
        type: equals_text
        param1: "1"
```

`params.*.ObjectLineID` values may be `{ field: CODE }` and resolve to the line ID. `RoleID1` / `RequestStatusID1` (Change role and status) may be `{ role: requestor }` / `{ status: updating }`. `NotificationID1` / `NotificationID2` may be `{ notification: assigned }` ([notifications](#notifications-specnotificationsyaml)). Condition `type` slugs match update actions. Do not gate on **memo** `is_not_empty` — that tests the memo record ID, not HTML ([object-actions.md](../entities/object-actions.md#objectactioncondition)).

**IDs:** `objectActions`, `objectActionParams` (`action/paramCode`), `objectActionConditions` (`action/field/type`), `workflowStepObjectActions` (`action/stepName`).

## Periodics (`spec/periodics.yaml`)

Optional fragment for **Periodic** + optional **Scheduler** CRON. See [entities/integrations.md](../entities/integrations.md#periodic). Recipe: [add-periodic.md](../../recipes/add-periodic.md).

Periodic selects last-version requests of **this** object, filters them, and runs ordered `PeriodicAction`s. `cron` (Quartz **7-field**) emits `Scheduler` / `SchedulerLine` (`spPeriodicExecute`) / `PeriodicID` param. Omit `cron` for on-demand `Execute_Periodic` only.

```yaml
periodics:
  - key: load_fio_hourly
    name: Load FIO transactions
    requestType: completed   # all | in_progress | completed  (or 0 / 10 / 20)
    cron: "0 0 * ? * * *"    # hourly at :00, Europe/Prague
    conditions:
      - field: TYPE
        type: equals_text
        param1: FIO
    actions:
      - key: start_load
        name: Start load
        typeCode: spEndPointRunNodeJSMain
        order: 10
        params:
          CustomJS: |
            import { XeeloGraphQLClient } from "@xeelo/graphql-client";
            export async function main() { return "OK"; }
          EndPointRunWait: "1"
          EndPointRunTimeout: "300000"
        conditions:
          - field: TYPE
            type: equals_text
            param1: FIO
```

Include in `xeelo-spec.yaml`:

```yaml
includes:
  - spec/periodics.yaml
```

Node.js type is **`spEndPointRunNodeJSMain`** (not `…Last`). Missing wait/timeout params default to `"1"` / `"60000"`. Condition slugs match update actions. `params.*.ObjectLineID` may be `{ field: CODE }`. `NotificationID1` / `NotificationID2` may be `{ notification: key }` (single vs summary). GraphQL mutate from Periodic **must refresh** (`withRefresh: true` or `createType`); ObjectAction self-update must not ([nodejs.md](../entities/nodejs.md#periodic--graphql-mutate-must-refresh)).

**IDs:** `periodics`, `periodicConditions` (`periodic/field/type`), `periodicActions` (`periodic/action`), `periodicActionParams` (`periodic/action/paramCode`), `periodicActionConditions` (`periodic/action/field/type`), `schedulers` (periodic key), `schedulerLines` (`periodic/execute`), `schedulerLineParams` (`periodic/execute/PeriodicID`).

### Extract from transfer

```bash
python scripts/extract-object-transfer-to-spec.py \
  projects/<name>/output/object-transfer.xml \
  -o projects/<name>

python scripts/extract-object-transfer-to-spec.py \
  path/to/object-transfer.xml \
  --object-id <objectId> \
  -o projects/<name>
```

After import on site: re-export object from Admin, extract again, commit updated `ids.explicit` (including `roles` / `statuses` maps).

## onGrid

Semantics (modules × Grid/Table × size, rows `T`/`A`–`E`, new-object default): [ongrid.md](../entities/ongrid.md). This section is the spec grammar.

### `onGrid.fields` (by field `code`)

Sets **ObjectLine** display flags for inbox grid:

| Spec key | DB column |
|----------|-----------|
| `allowed` | `ObjectLineOnGridIsAllowed` |
| `name` | `ObjectLineOnGridName` |
| `isTag` | `ObjectLineOnGridIsTag` — **only** `text` / `textarea` (types 3, 4). Field values become request-grid tag filters (AND). See [object-line-types.md](../entities/object-line-types.md#on-grid-tag). |
| `isSearch` | `ObjectLineOnGridIsSearch` — typed search; types 1, 2, 3, 4, 8, 11, 12, 14, 15, 19, 20 — [object-line-types.md](../entities/object-line-types.md#admin-canset-objectline) |
| `isTotal` | `ObjectLineOnGridIsTotal` — **number** (12) only. Inbox Summarization sums the stored slot. See [object-line-types.md](../entities/object-line-types.md#on-grid-total). |

```yaml
onGrid:
  fields:
    CATEGORY:
      allowed: true
      isTag: true
    AMOUNT:
      allowed: true
      isTotal: true
    INCOME:
      allowed: false
      isTotal: true
```

`CATEGORY` must be `type: text` or `textarea`. Extract emits `onGrid.fields` when `allowed`, `isTag`, `isSearch`, or `isTotal` is set (tag-only / total-only helpers: `allowed: false`). After deploy, **/publish** so the tag / total / sort cache SQL is rebuilt.

Inbox cells parse `[badge:{CustomColorCode}_{text}]` as a colored chip (`.xe-badge-{code}`). Do **not** store badge tokens on an `isTag` line — use a separate display text line (`isTag: false`). Combo cannot be `isTag`. See [object-line-types.md](../entities/object-line-types.md#on-grid-badge).

### `onGrid.layouts`

Creates **ObjectLineOnGrid** rows — one per layout variant (`size` + `type` + `module`). The same field or system line may appear in several layouts; each variant is its own row.

Which triples exist in cache, rows `T`/`A`–`E`, and the **seven layouts to write for a new object**: [ongrid.md](../entities/ongrid.md). YAML below is the grammar only.

`ids.explicit.objectLineOnGrid` keys:

- field: `{size}/{type}/{module}/{code}`
- system line: `{size}/{type}/{module}/sys:{code}` (prefix `sys:` so it cannot collide with a field code)

| Spec key | DB column |
|----------|-----------|
| `size` | `ObjectLineOnGridSize` — `Small` (phone), `Medium` (tablet), `Large` (desktop) |
| `type` | `ObjectLineOnGridType` — `Grid` or `Table` |
| `module` | `ObjectLineOnGridModule` — `Items`, `Tasks`, `MobileItems`, `MobileTasks`, `Relation`, `RelationMap`. Not every module has Grid+Table and L/M/S — see [ongrid.md](../entities/ongrid.md#objectline-catalog-request-inbox). |
| `placements[].row` | `ObjectLineOnGridRow` — `T`, `A`–`E` ([ongrid.md](../entities/ongrid.md#rows-t-a-b-c-d-e)) |
| `placements[].columns[].field` | resolves to `ObjectLineID` — **xor** `systemLine` |
| `placements[].columns[].systemLine` | resolves to `SystemLineID` — **xor** `field`. Codes: [`SystemLine.json`](../../data/enums/SystemLine.json) (`role` = 40, `status` = 50, …). Row has **no** `ObjectLineID`. |
| `position` | `ObjectLineOnGridPosition` — start column in percent (0–99) |
| `length` | `ObjectLineOnGridLength` — column span in percent (1–100); row columns should sum to 100 |
| `valueWidth` | `ObjectLineOnGridValueWidth` — percent of the cell for the **value**. `0` = auto. **`100` + Horizontal = hide the column label** (Admin ValueWidthLabelHidden). |
| `labelType` | `ObjectLineOnGridLabelType` — **1 Horizontal** (default), **2 Vertical**. SQL also has `0` None; Admin does not offer it — do not spec `0`. |

To show chips without a column title on **Grid**, set `labelType: 1` and `valueWidth: 100`. Role / Status on the inbox are typically that plus `systemLine: role` / `systemLine: status` on the right of the title row.

```yaml
onGrid:
  layouts:
  - size: Large
    type: Grid
    module: Items
    placements:
    - row: T
      columns:
      - field: REQ_NO
        position: 0
        length: 80
        valueWidth: 0
        labelType: 1
      - systemLine: role
        position: 80
        length: 10
        valueWidth: 100
        labelType: 1
      - systemLine: status
        position: 90
        length: 10
        valueWidth: 100
        labelType: 1
```

**SystemLine vs ObjectLine.** Inbox Role, Status, Requestor, dates, … are **SystemLine** columns, not object fields. Extract used to drop rows with `ObjectLineID` null; generate now emits `SystemLineID` from `systemLine`. After upgrading the KB, **/download-db** so `ids.explicit.objectLineOnGrid` picks up `sys:role` keys — otherwise generate would allocate new IDs and duplicate columns.

**Alignment** of a system column is `SystemLine.SystemLineAlignmentID` (0 left, 1 right, 2 center) — **site-wide**, not per object. It is not a column on `ObjectLineOnGrid`. Object Transfer cannot upsert `SystemLine` (no identity; not a transfer table). Field columns use `ObjectLine.ObjectLineOnGridAlignmentID` instead (not yet in spec).

**Grid vs Table**

| `type` | How `placements[].row` renders |
|--------|--------------------------------|
| **Grid** | Each letter (`T`, `A`–`E`) is a visual row; cards wrap/stack. |
| **Table** | Always **one** visual row. Pseudo-rows from the spec **do not wrap** — columns stay on a single line and the table **scrolls horizontally**. |

Use **Grid** when the inbox card should stack. Use **Table** for a spreadsheet-like list. Medium/Small wrap is the same spec for both (`T`/`A`/`B`); Grid stacks letters, Table still one line of columns. Catalog: [ongrid.md](../entities/ongrid.md).

## Generate

```bash
python scripts/generate-object-transfer.py my-spec.yaml \
  -o output/object-transfer.json
```

See [object-transfer-format.md](object-transfer-format.md).
