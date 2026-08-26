# Object Model

Form definition entities — core of every Xeelo object.

Schemas: [`data/schemas/`](../data/schemas/) · Labels: [`data/entity-labels.json`](../data/entity-labels.json)

## Object

**Table:** `Object` · **UI:** Object

Root form definition. Belongs to Company + ObjectType.

| Column | Semantics |
|--------|-----------|
| `ObjectName` | Display name (canonical; translations in [localization.md](localization.md)) |
| `CompanyID` | Owning company |
| `ObjectTypeID` | Category |
| `ObjectCode` | Optional unique code |
| `ObjectTreeIcon` | Font Awesome 6.5.1 class string (`fa-{id} fa-{variant} fa-fw`). Spec: `object.icon` |
| `ObjectTreeColor` | Treeview icon color = `CustomColor.CustomColorCode` (not HEX). Spec: `object.color` |
| `RequestTitleObjectLineID` | ObjectLine whose value is the **request title** in GUI (inbox, header, links). Spec: `object.requestTitleField` |
| `ObjectGridSortObjectLineID` | Default inbox sort line. Spec: `object.gridSort.field` (field **code**) |
| `ObjectGridSortType` | `ASC` or `DESC`. Spec: `object.gridSort.type`. Admin also offers `None` (no line sort). After precompile, date (type 8) is parsed as `date`; tie-break is always `RequestID DESC`. A user filter can override. Subgrid analog: `ObjectSubGridSortObjectSubLineID` / `ObjectSubGridSortType` (not in spec yet). |
| `IsActive` | Inactive = hidden from Admin, Inbox, Browser |

## Company and ObjectType (tree)

**Company** (`company.name`, optional `company.icon` → `CompanyTreeIcon`) groups objects. `CompanyTreeColor` still exists in SQL/Admin as **Color (obsolete)** — User GUI company tabs use the icon only; do not put it in spec.

**ObjectType** name stays `object.objectType`. Tree visuals are a sibling block:

| Spec | Column | Notes |
|------|--------|-------|
| `objectType.icon` | `ObjectTypeTreeIcon` | FA 6.5.1 class string |
| `objectType.color` | `ObjectTypeTreeColorBack` | Live Admin “Icon Color”; treeview CSS |
| — | `ObjectTypeTreeColorFont` | **obsolete** — do not spec |

Palette: [`data/enums/CustomColor.json`](../data/enums/CustomColor.json). Search icons: `python scripts/search-fa-icons.py --query bank` ([`data/fontawesome-icons.json`](../data/fontawesome-icons.json)). Full spec: [spec-format.md](../transfer/spec-format.md#tree-icons-and-colors).

## Layout: Tab → Section → Line

### ObjectLineTab

**UI:** Object Tab

| Column | Semantics |
|--------|-----------|
| `ObjectLineTabName` | Tab label (canonical; translations in [localization.md](localization.md)) |
| `ObjectLineTabPlacement` | `0` = left, `1` = right |
| `ObjectLineTabOrder` | Sort order |
| `ObjectLineTabAlwaysHidden` | Hide the whole tab. Typical for a tab that only holds helper lines. Spec: `layout.tabs[].alwaysHidden`. **Not** the same as template `hidden: true` (extended validation). |

Note: no direct `ObjectID` FK — association is via sections → lines → object.

### ObjectLineSection

**UI:** Object Section

| Column | Semantics |
|--------|-----------|
| `ObjectSectionName` | Section heading (canonical; translations in [localization.md](localization.md)) |
| `ObjectLineTabID` | Parent tab |
| `ObjectSectionOrder` | Sort order |
| `ObjectSectionWidth` | Section width in percent (1–100) |

### ObjectLine

**UI:** Object Line — individual field/control.

| Column | Semantics |
|--------|-----------|
| `ObjectLineName` | Field label (canonical; translations in [localization.md](localization.md)) |
| `ObjectLineTypeID` | Control type (1–20) — [object-line-types.md](object-line-types.md), [`ObjectLineType.json`](../data/enums/ObjectLineType.json) |
| `ObjectLineSlot` | Unique slot per object (required for most active lines; not 5, 6, 13, 16, 17) |
| `ObjectLineOrder` | Display order |
| `ObjectLineTypeWidth` | Field width in percent (1–100) |
| `ObjectLineCode` | Optional stable code (GraphQL, integrations). After insert, Admin often persists `line_{ObjectLineID}_{slug}` even if the transfer sent a shorter code. GraphQL uses the stored value — take it from env after `/download-db`. |
| `ObjectLineIsHidden` | Hide this line in GUI (definition-level). Spec: `fields[].alwaysHidden`. Distinct from template `hidden: true` / `extended.hidden`. Helper fields often live on an `alwaysHidden` tab instead. |
| `IsActive` | Soft-disable the line. Spec: `fields[].isActive: false`. Object Transfer does not delete. Distinct from `alwaysHidden` (line still active, just not shown). |
| `ObjectLineOnGridIsAllowed` | Line may appear on the request grid — [ongrid.md](ongrid.md) |
| `ObjectLineOnGridIsTag` | Tag filter: field **values** as chips on the request grid. Admin enables only types **3, 4** — [object-line-types.md](object-line-types.md#on-grid-tag) |
| `ObjectLineOnGridIsSearch` | Typed search on the request grid (types 3, 4, 8, 12) |
| `ObjectLineOnGridIsTotal` | Sum this **number** line in inbox Summarization. Spec: `onGrid.fields.<code>.isTotal`. Type 12 only — [object-line-types.md](object-line-types.md#on-grid-total) |

Type-dependent extras (precision, source, attachment, preview, web frame, unique, …): [object-line-types.md](object-line-types.md). Spec slugs: [`data/field-type-mapping.json`](../data/field-type-mapping.json). Display-name translations: [localization.md](localization.md).

## Template: ObjectDefault + ObjectDefaultLine

**UI:** Object Template / Template Line

Every usable object needs a default template linking the object to a workflow.

| ObjectDefault | Semantics |
|---------------|-----------|
| `ObjectID` | Object |
| `WorkflowID` | Workflow for new requests |
| `ObjectDefaultIsDefault` | Exactly one `=1` per object |
| `ObjectDefaultReopenTypeID` | After **create** save: stay open or close. Spec: `templates[].reopenOnSave`. Catalog [`ReopenActionType.json`](../data/enums/ReopenActionType.json) (`none`/`close` = NULL, `open-only-everytime` = 1, `open-with-actions` = 2, `open-only-assigned` = 3). Same enum on `ObjectUpdateActionReopenTypeID` and `WorkflowStepActionReopenTypeID`. Runtime uses the template (or update-action) value on **new** requests (`isNew`); an already-saved request always stays Open only (everytime). ID 3 is not sent to the frontend — the backend rewrites it to OpenOnly or Close from Inbox assignment (`EditableWorkflow`). |

| ObjectDefaultLine | Semantics |
|-------------------|-----------|
| `ObjectLineID` | Which field |
| `ObjectDefaultLineValidationID` | `1` Mandatory, `2` Optional (always emit; never omit), `9` Extended — [object-line-types.md](object-line-types.md#validation) |
| `ObjectDefaultLineValidationExt*Condition` | Independent hide / disable / mandatory expressions — [xeelo-grammar.md](xeelo-grammar.md) |
| `ObjectDefaultLineIsDisabled` | Admin **Always disabled** on this template line. Spec: `templates.fields.<code>.alwaysDisabled` |
| `ObjectDefaultLineLookupID` | Lookup map (dotazovací mapa) |
| `ObjectDefaultLineLookupObjectLineID` | Source field — whose value is matched |
| `ObjectDefaultLineLookupFilterObjectLineID` | Optional filter field — further restricts the map row |
| `ObjectDefaultLineValue` | Default value (not used for description memo). Spec: `templates.fields.<code>.defaultValue` — [object-line-types.md](object-line-types.md#default-value-and-filter) |
| `ObjectDefaultLineValueFilter` | Default filter for combo/radio/multi. Spec: `defaultFilter`. Omit unless asked |
| `ObjectDefaultLineDescMemo` | Description memo (16) default — **HTML**. Spec: `defaultValue` on `description_memo` |
| `ObjectDefaultLineClientCalculationTypeID` | Client calc 1–8 — [object-line-types.md](object-line-types.md#client-calculations) |
| `ObjectDefaultLineClientCalculation` | Math/String expr without `1#`/`2#` prefix — [xeelo-grammar.md](xeelo-grammar.md) |
| `ObjectDefaultLineClientCalcDelay` | Debounce ms on the **source** line. Spec: `calcDelay`. Omit = runtime 400. Do not set unless asked — [object-line-types.md](object-line-types.md#client-calc-delay-and-confirm) |
| `ObjectDefaultLineIsClientCalcConfirm` | Refresh button on text/number source. Spec: `calcConfirm`. Omit = off. Do not set unless asked |
| `ObjectDefaultLineCalculationTypeID` | Server calc **51+** ([`ObjectDefaultLineCalculationType.json`](../data/enums/ObjectDefaultLineCalculationType.json)). Spec does not emit it — [object-line-types.md](object-line-types.md#server-calculations) |
| `ObjectDefaultLineCalculation` | Server calc formula (for example Server-SubConcat **52**: `id{type5LineId},id{subLineId}`) |
| `ObjectDefaultLineHint` | Runtime hint for users (plain or HTML). Spec: `templates.fields.<code>.hint`. All types except empty space (6). Localized via `languageTable.templateHints`. Distinct from `description_memo` `defaultValue`. Subgrid template hint: `ObjectSubDefaultLineHint` (`subgrids.*.templates[].fields.*.hint`). |
| `ObjectDefaultLineAutoNumberID` | Bind to a catalog autonumber (sequence) — [Autonumber](#autonumber) |

Which template capabilities apply depends on the line type. Combo / radio / multi always need a **reference** on `ObjectLine`. A **lookup** on the template line may sit on the same field — it fills the value from another line.

**`ObjectDefaultLineCalculationOrder`** (child of `ObjectDefault`, not of `ObjectDefaultLine`): which lines run on refresh and in what order. Required for type-5 parents and server calcs **51–100**. Spec/generator do not emit it — [object-line-types.md](object-line-types.md#calculation-order).

### Create-form access (ObjectDefaultAccess)

**Table:** `ObjectDefaultAccess` · **UI:** Template → Access (Visible / Editable dual-list)

Per-line (optional subline) flags while the request is **created** from this template. Same Admin pattern as workflow step access and update-action access — **not** `templates.fields.hidden` / `alwaysDisabled`.

| Column | Refresh insert | Semantics |
|--------|----------------|-----------|
| `ObjectLineIsVisibleCreate` | `1` | Field visible on create |
| `ObjectLineIsEditableCreate` | `1` | Field editable on create |

Site refresh inserts a row per (template, line) as **visible and editable**. **Object Transfer does not run that refresh.** A missing `ObjectDefaultAccess` row means the line is **hidden on create**. For a **new** line, emit `templates[].access` with `visible: true` and `editable: true` even though that matches the refresh default. After `/download-db`, extract drops those default rows from spec.

On later loops, list only exceptions (hide or lock). `editable: true` forces `visible: true`. Optional `access[].sublineId` (`ObjectSubLineID`) for a subgrid **column**; `ObjectLineID` is still the parent type-5 line. See [Subgrid](#subgrid).

Spec: `templates[].access` — see [spec-format.md](../transfer/spec-format.md#templates-spectemplatesyaml). Distinct from:

| Spec | Table | When |
|------|--------|------|
| `templates[].access` | ObjectDefaultAccess | Create form (static dual-list) |
| `workflow.steps[].access` | WorkflowStepAccess | After create, on a step |
| `updateActions[].access` | ObjectUpdateAccess | EditableUpdate (new version) |
| `templates.fields.*.hidden` / `extended.hidden` | ObjectDefaultLine | Extended validation (expression) |
| `templates.fields.*.alwaysDisabled` | ObjectDefaultLine | Always disabled on the template line |
| `fields[].alwaysHidden` | ObjectLine | Definition-level hide |

## Reference (ObjectLineSource)

**Tables:** `ObjectLineSource`, `ObjectLineSourceValue`, `ObjectLineSourceRefObject`

**Bind:** `ObjectLine.ObjectLineSourceID` (+ optional `ObjectLineSourceFilterObjectLineID` via spec `reference.filterField`)

| Režim | Child table | Popis |
|-------|-------------|-------|
| System (`ObjectLineSourceTypeID >= 10`) | — | Site-preexisting (User List, Company List, …) |
| Table + values | `ObjectLineSourceValue` | Pevně nadefinované položky; optional `values[].filter` (comma-split) |
| Table + refObject | `ObjectLineSourceRefObject` | Dynamicky z requestů referencovaného objektu; optional `refObject.lines.valueFilter` matched against the consuming `filterField` |

refObject **Request Type** (`ObjectLineSourceRefObjectRequestTypeID`, spec `refObject.requestType`, default `all`) filters which request versions appear in the combo. Not the same as request Create/Update (`RequestTypeID` 1/2/3). Enum: [`ObjectLineSourceRefObjectRequestType.json`](../data/enums/ObjectLineSourceRefObjectRequestType.json).

| ID | Admin | Spec | Combo options |
|----|-------|------|----------------|
| 0 | All | `all` (default) | last version of each request |
| 1 | Only completed | `completed` | last version only when it is completed |
| 2 | Only inprogress | `in-progress` | last version only when it is not completed |

The generator also writes deprecated `ObjectLineSourceRefObjectIsOnlyCompleted` (`1` iff `completed`); runtime uses Request Type.

`ObjectLineSourceStyleID` (`styleId`): 1 Name, 2 Bind - name, 3 Name (value), **4 Value (default for new references)**.

Recipe: [`recipes/add-reference-field.md`](../recipes/add-reference-field.md)

## Lookup (query map)

**Tables:** `ObjectLineLookup`, `ObjectLineLookupValue`

Bound on **ObjectDefaultLine**, not as a picklist. When the Source field (or Filter field) changes, runtime matches a map row and writes `ReturnValue` into this line.

| ObjectLineLookupValue | Semantics |
|-----------------------|-----------|
| `ObjectLineLookupSourceValue` | Match key = current value of Source field (not a combo label) |
| `ObjectLineLookupSourceValue1` | Range end when Match = Numeric range |
| `ObjectLineLookupReturnValue` | Value written to this field |
| `ObjectLineLookupFilterValue` | Optional **exact** match against the Filter field (`==`; empty filter uses rows with FilterValue NULL) |

Match types ([`ObjectLineLookupMatch.json`](../data/enums/ObjectLineLookupMatch.json)): **1 Exact string**, **2 Numeric range**.

Comma-split “value is among a list on the option” is **reference** filter (`ObjectLineSourceValueFilter`), not lookup filter.

Admin enables lookup on types 1, 2, 3, 7, 8, 12, 14, 15, 19, 20. Source field is required once a lookup is selected.

On combo / radio / multi, also bind a **reference** whose option binds include the lookup return values.

Recipe: [`recipes/add-lookup-field.md`](../recipes/add-lookup-field.md)

## Autonumber

**Table:** `ObjectLineAutoNumber` · **UI:** Admin / Objects / Autonumber

Site-wide **sequence** (like a database sequence), not a field type. Define the catalog once, then bind it on a **template line** (`ObjectDefaultLineAutoNumberID`). The same autonumber shares one counter across objects and templates.

| Column | Semantics |
|--------|-----------|
| `ObjectLineAutoNumberDescription` | Name shown when picking the autonumber on a template line |
| `ObjectLineAutoNumberFormat` | Mask. One contiguous run of `#` is the zero-padded number; prefix/suffix sit around it. After generate, `YYYY` / `YY` / `MM` / `DD` are replaced with the current date |
| `ObjectLineAutoNumberNext` | Next integer; incremented by one on generate |
| `ObjectLineAutoNumberResetTypeID` | Optional. **1 Yearly** — counter resets per calendar year ([`ObjectLineAutoNumberResetType.json`](../data/enums/ObjectLineAutoNumberResetType.json)). Per-year next values live in `ObjectLineAutoNumberReset` (runtime; **not** in transfer) |

Admin enables autonumber only on **text** (type 3). Input mask / length cannot be set on the same template line.

**When the value is written:** insert stores the **format string** (still containing `#`) as a placeholder. Request refresh generates the number only while the stored value still contains `#`. Alternative: server calc **95 Server-AutonumberGenerate** (when the field is empty). Spec does not emit that calc — bind the catalog on the template line.

Typical **request identifier**: text field + autonumber bind + Unique (below). Spec: `spec/autonumbers.yaml` + `templates.fields.<code>.autonumber` (or layout `fields[].autonumber` on a single default template). Recipe: [`recipes/add-autonumber-field.md`](../recipes/add-autonumber-field.md).

Subgrid template lines bind the same catalog (`ObjectSubDefaultLineAutoNumberID`). Spec: `subgrids.*.templates[].fields.*.autonumber`.

## Object Service

Site HTTP catalog (`ObjectService`) bound on the template line as **Client-Service**. Spec: `spec/object-services.yaml` + `templates.fields.<code>.clientCalculation` (`type: service`). [object-services.md](object-services.md). Recipe: [`add-client-service.md`](../../recipes/add-client-service.md).

## Unique

**Columns:** `ObjectLineUniqueID` (level), `ObjectLineIsUnique` (bit)

Uniqueness of a field **value** among **submitted** requests of this object (last version of each request code). Empty values are not checked. GraphQL line flag `unique` is 1 when `ObjectLineUniqueID` is not null — runtime follows UniqueID, not the bit. Spec `fields[].uniqueId` writes both (`ObjectLineUniqueID` + `ObjectLineIsUnique = 1`).

Levels ([`ObjectLineUnique.json`](../data/enums/ObjectLineUnique.json)):

| ID | Name | Scope |
|----|------|--------|
| 1 | Object level | all submitted requests of the object |
| 2 | Object / Template level | + same template |
| 3 | Object / Requestor level | + same requestor |
| 4 | Object / Template / Requestor level | template and requestor |

Admin Unique on types **1, 2, 3, 4, 7, 8, 12, 14, 15**. Number compares parsed numeric value; checkbox only treats checked (`1`) as unique.

**Several unique lines** are not one tuple on the request: each unique field is checked **on its own** (unique(A) and unique(B), not unique(A,B)). Use **one** autonumber + `uniqueId` for a request identifier.

**Subgrid** unique is a boolean (`ObjectSubLineIsUnique`, no level). Several unique sublines **are** a composite key (AND) within that parent request. Spec/generator do not emit subgrid unique yet.

## Subgrid

**Tables:** `ObjectSub`, `ObjectSubLineTab`, `ObjectSubLineSection`, `ObjectSubLine` · **Parent line type:** 5 (`subgrid`) · **Templates:** `ObjectSubDefault`, `ObjectSubDefaultLine`

Embedded repeatable table. Not a child of `Object` — the header has no `ObjectID`. Binding is **`ObjectLine.ObjectSubID`** on a parent line of type 5 (no slot; not allowed on the request inbox grid).

```
ObjectLine (type 5)
└── ObjectSub                    # shared catalog; several parent lines may point here
    ├── ObjectSubLineTab → ObjectSubLineSection → ObjectSubLine
    ├── ObjectSubDefault → ObjectSubDefaultLine
    └── ObjectSubPrefill → ObjectSubPrefillData   # not in spec yet
```

Same type IDs and **same spec extras** as ObjectLine for every type in `ObjectSubLineType` (no 5 / 13 / 18). Spec keys stay `precision`, `reference`, `attachmentStorageId`, … — SQL is `ObjectSubLine*`. Exceptions: unique is a boolean; total types 3 and 12; slot skip is 6/16/17. [object-line-types.md](object-line-types.md#subgrid-columns-objectsubline). Recipe: [`recipes/add-subgrid.md`](../recipes/add-subgrid.md). Spec: [`spec/subgrids.yaml`](../transfer/spec-format.md#subgrids-specsubgridsyaml).

### Bind on the parent object

| Piece | Column | Spec |
|-------|--------|------|
| Embedding line | `ObjectLine.ObjectSubID` | `fields[].objectSub` (key in `subgrids:`) or `objectSubId` (existing/shared ID, no tree emit) |
| Which subgrid template new rows use | `ObjectDefaultLine.ObjectSubDefaultID` | `templates.fields.<code>.subgridTemplate` (requires `objectSub:` key) |
| Prefill | `ObjectDefaultLine.ObjectSubPrefillID` | not in spec yet |

Admin capability “Subgrid template / prefill” applies only to type 5.

### Sharing

Uncommon but valid: several objects (or several type-5 lines) set `ObjectSubID` to the **same** `ObjectSub`. OT `ObjectLine → ObjectSub` is include-for-transfer, not exclusive ownership. The second object should use `objectSubId:` only — do not emit a second tree with new Orig. IDs.

### Access (ObjectLine + ObjectSubLine)

Create / workflow step / update-action access tables all have required `ObjectLineID` and optional `ObjectSubLineID`:

- `ObjectDefaultAccess`
- `WorkflowStepAccess`
- `ObjectUpdateAccess`

`ObjectLineID` is **this object’s** type-5 embedding line. `ObjectSubLineID` is a column of the (possibly shared) `ObjectSub`. Shared tree ≠ shared access: object A and B have different parent lines.

Spec: `access[].field` + optional `access[].sublineId`. Orig. ID keys `{field}` or `{field}/sub{sublineId}`. Row without subline = the subgrid widget; row with subline = that column. Reuse the existing access Orig. ID for the same (template/step/action, line, subline).

**New type-5 line:** emit create access (`templates[].access`, visible+editable) **and** `workflow.steps[].access` on **every** step that should show the widget. Generator copies that parent access onto each `ObjectSubLine` (the add-row modal). Object Transfer does not seed access; a missing **widget** row hides the grid; a missing **column** row leaves the modal empty. Same rule as any new ObjectLine.

### vs request

| | Request (`ObjectLine`) | Subgrid (`ObjectSubLine`) |
|--|------------------------|---------------------------|
| Type extras | `precision`, `reference`, … on `ObjectLine*` | **same spec keys** on `ObjectSubLine*` (types 5 / 13 / 18 do not exist) |
| Unique | `uniqueId` 1–4; each field checked on its own | boolean; several unique columns = **composite AND** in the parent request |
| Autonumber | `ObjectDefaultLineAutoNumberID` | same catalog; `ObjectSubDefaultLineAutoNumberID` |
| Inbox on-grid | type 5 **not** allowed | `subgrids.<key>.onGrid` → `ObjectSubLine` flags + `ObjectSubLineOnGrid` (tag 3/4; total types **3 and 12**) |
| Grid sort | `ObjectGridSort*` | `ObjectSubGridSort*` — not in spec yet |
| Workflow | object workflow | rows live under the parent request; no own workflow |
| Prefill | — | `ObjectSubPrefill` — not in spec yet |
| Width | field 1–100 % | `ObjectSubWidth` = add/edit-row **modal** width; default **80** (Admin 50–100). Grow the form with tabs/sections or stacked fields, not a wider modal |
| Label | `IsHorizontal` | type-5 label always in the SubGrid header |
| GraphQL | `ObjectCode` | same `Select_` / `Mutate_` prefixes from **`ObjectSubCode`** |
| Generate + combo Multiselect | — | subgrid-only (below) |

Generator emits the tree + parent FK + `ObjectSubDefaultID` bind + `ObjectSubDefaultLine` validation / hint / autonumber / lookup / client-calc / `defaultValue` / `defaultFilter` / `calcDelay` / `calcConfirm` + `onGrid` + ObjectLine-style type extras on `ObjectSubLine` (`precision`, `reference`, attachment, preview, …) + `languageTable.subgrids`. Not yet: unique/gridSort, Generate/Multiselect, prefill, comments on `ObjectSub*`.

### Generate + combo Multiselect

`ObjectSub` can enable **Generate**. A combobox column (`ObjectSubLine` type 1, maybe search) can enable **Multiselect**. That is **not** request type 20 `checkbox_multiselect`.

With Generate on, the user picks several číselník values on that combo; runtime **creates one subgrid row per selected value** (typically filling that combo). Without Generate, Multiselect on the combo does nothing useful — a normal sub-row is single-select. Exact SQL names are not in spec yet (`ObjectSubIsGenerate` / `ObjectSubLineIsMultiSelect` or similar).

### GraphQL and notifications

Sanitize `ObjectSubCode` the same way as `ObjectCode`. Query/mutation names use that code (`Select_{code}`, `Mutate_{code}`), not the parent `ObjectLineCode`. Email tokens: `{RequestSubGrid,Width,ObjectLineID,ObjectSubLineID,...}`.

## Update actions

**Tables:** `ObjectUpdateAction`, `ObjectUpdateAccess`, …

User-facing updates on **completed** requests create a new request version. Defined on the object; optional workflow on the action drives the new version.

See [update-actions.md](update-actions.md) · recipe [add-update-action.md](../recipes/add-update-action.md)

## Object actions

**Tables:** `ObjectAction`, `ObjectActionParam`, `ObjectActionCondition`, `WorkflowStepObjectAction`

Server automation after save/workflow (`spObjectActionExecute`). Distinct from update actions and from form Button lines.

See [object-actions.md](object-actions.md) · recipe [add-object-action.md](../recipes/add-object-action.md) · GraphQL [graphql.md](graphql.md)

## DB transfer

All object model tables above are in transfer scope — see [`data/transfer-tables.json`](../data/transfer-tables.json).
