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
| `RequestTitleObjectLineID` | ObjectLine whose value is the **request title** in GUI (inbox, header, links). Spec: `object.requestTitleField` |
| `IsActive` | Inactive = hidden from Admin, Inbox, Browser |

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
| `ObjectLineOnGridIsAllowed` | Line may appear on the request grid |
| `ObjectLineOnGridIsTag` | Tag filter: field **values** as chips on the request grid. Admin enables only types **3, 4** — [object-line-types.md](object-line-types.md#on-grid-tag) |
| `ObjectLineOnGridIsSearch` | Typed search on the request grid (types 3, 4, 8, 12) |

Type-dependent extras (precision, source, attachment, preview, web frame, unique, …): [object-line-types.md](object-line-types.md). Spec slugs: [`data/field-type-mapping.json`](../data/field-type-mapping.json). Display-name translations: [localization.md](localization.md).

## Template: ObjectDefault + ObjectDefaultLine

**UI:** Object Template / Template Line

Every usable object needs a default template linking the object to a workflow.

| ObjectDefault | Semantics |
|---------------|-----------|
| `ObjectID` | Object |
| `WorkflowID` | Workflow for new requests |
| `ObjectDefaultIsDefault` | Exactly one `=1` per object |

| ObjectDefaultLine | Semantics |
|-------------------|-----------|
| `ObjectLineID` | Which field |
| `ObjectDefaultLineValidationID` | `1` Mandatory, `2` Optional (always emit; never omit), `9` Extended — [object-line-types.md](object-line-types.md#validation) |
| `ObjectDefaultLineValidationExt*Condition` | Independent hide / disable / mandatory expressions — [xeelo-grammar.md](xeelo-grammar.md) |
| `ObjectDefaultLineIsDisabled` | Admin **Always disabled** on this template line. Spec: `templates.fields.<code>.alwaysDisabled` |
| `ObjectDefaultLineLookupID` | Lookup map (dotazovací mapa) |
| `ObjectDefaultLineLookupObjectLineID` | Source field — whose value is matched |
| `ObjectDefaultLineLookupFilterObjectLineID` | Optional filter field — further restricts the map row |
| `ObjectDefaultLineValue` | Default value (not used for description memo) |
| `ObjectDefaultLineDescMemo` | Description memo (16) default — **HTML** |
| `ObjectDefaultLineClientCalculationTypeID` | Client calc 1–8 — [object-line-types.md](object-line-types.md#client-calculations) |
| `ObjectDefaultLineClientCalculation` | Math/String expr without `1#`/`2#` prefix — [xeelo-grammar.md](xeelo-grammar.md) |
| `ObjectDefaultLineHint` | Runtime hint text for users |
| `ObjectDefaultLineAutoNumberID` | Bind to a catalog autonumber (sequence) — [Autonumber](#autonumber) |

Which template capabilities apply depends on the line type. Combo / radio / multi always need a **reference** on `ObjectLine`. A **lookup** on the template line may sit on the same field — it fills the value from another line.

### Create-form access (ObjectDefaultAccess)

**Table:** `ObjectDefaultAccess` · **UI:** Template → Access (Visible / Editable dual-list)

Per-line (optional subline) flags while the request is **created** from this template. Same Admin pattern as workflow step access and update-action access — **not** `templates.fields.hidden` / `alwaysDisabled`.

| Column | Refresh insert | Semantics |
|--------|----------------|-----------|
| `ObjectLineIsVisibleCreate` | `1` | Field visible on create |
| `ObjectLineIsEditableCreate` | `1` | Field editable on create |

Site refresh inserts a row per (template, line) as **visible and editable**. Spec `templates[].access` lists only exceptions (hide or lock). `editable: true` forces `visible: true`.

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

Subgrid template lines can bind the same catalog (`ObjectSubDefaultLineAutoNumberID`). Spec/generator do not emit subgrid autonumbers yet.

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

**Table:** `ObjectSub` · **Line type:** 5 (Sub-grid)

Embedded repeatable table within a parent object line. Has own tabs, sections, lines, templates.

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
