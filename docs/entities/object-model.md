# Object Model

Form definition entities — core of every Xeelo object.

Schemas: [`data/schemas/`](../data/schemas/) · Labels: [`data/entity-labels.json`](../data/entity-labels.json)

## Object

**Table:** `Object` · **UI:** Object

Root form definition. Belongs to Company + ObjectType.

| Column | Semantics |
|--------|-----------|
| `ObjectName` | Display name |
| `CompanyID` | Owning company |
| `ObjectTypeID` | Category |
| `ObjectCode` | Optional unique code |
| `IsActive` | Inactive = hidden from Admin, Inbox, Browser |

## Layout: Tab → Section → Line

### ObjectLineTab

**UI:** Object Tab

| Column | Semantics |
|--------|-----------|
| `ObjectLineTabName` | Tab label |
| `ObjectLineTabPlacement` | `0` = left, `1` = right |
| `ObjectLineTabOrder` | Sort order |

Note: no direct `ObjectID` FK — association is via sections → lines → object.

### ObjectLineSection

**UI:** Object Section

| Column | Semantics |
|--------|-----------|
| `ObjectSectionName` | Section heading |
| `ObjectLineTabID` | Parent tab |
| `ObjectSectionOrder` | Sort order |
| `ObjectSectionWidth` | Section width in percent (1–100) |

### ObjectLine

**UI:** Object Line — individual field/control.

| Column | Semantics |
|--------|-----------|
| `ObjectLineName` | Field label |
| `ObjectLineTypeID` | Control type (1–20) — [object-line-types.md](object-line-types.md), [`ObjectLineType.json`](../data/enums/ObjectLineType.json) |
| `ObjectLineSlot` | Unique slot per object (required for most active lines; not 5, 6, 13, 16, 17) |
| `ObjectLineOrder` | Display order |
| `ObjectLineTypeWidth` | Field width in percent (1–100) |
| `ObjectLineCode` | Optional stable code (GraphQL, integrations) |

Type-dependent extras (precision, source, attachment, preview, web frame, unique, …): [object-line-types.md](object-line-types.md). Spec slugs: [`data/field-type-mapping.json`](../data/field-type-mapping.json).

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
| `ObjectDefaultLineLookupID` | Lookup source (dotazovací mapa / static list) |
| `ObjectDefaultLineLookupObjectLineID` | Source field for query-map lookup |
| `ObjectDefaultLineValue` | Default value (not used for description memo) |
| `ObjectDefaultLineDescMemo` | Description memo (16) default — **HTML** |
| `ObjectDefaultLineClientCalculationTypeID` | Client calc 1–8 — [object-line-types.md](object-line-types.md#client-calculations) |
| `ObjectDefaultLineClientCalculation` | Math/String expr without `1#`/`2#` prefix — [xeelo-grammar.md](xeelo-grammar.md) |
| `ObjectDefaultLineHint` | Runtime hint text for users |

Which template capabilities apply depends on the line type. Combo-box fields use **either** reference on `ObjectLine` **or** lookup on template line — not both.

## Reference (ObjectLineSource)

**Tables:** `ObjectLineSource`, `ObjectLineSourceValue`, `ObjectLineSourceRefObject`

**Bind:** `ObjectLine.ObjectLineSourceID` (+ optional `ObjectLineSourceFilterObjectLineID`)

| Režim | Child table | Popis |
|-------|-------------|-------|
| System (`ObjectLineSourceTypeID >= 10`) | — | Site-preexisting (User List, Company List, …) |
| Table + values | `ObjectLineSourceValue` | Pevně nadefinované položky |
| Table + refObject | `ObjectLineSourceRefObject` | Dynamicky z requestů referencovaného objektu |

`ObjectLineSourceStyleID` (`styleId`): 1 Name, 2 Bind - name, 3 Name (value), **4 Value (default for new sources)**.

Recipe: [`recipes/add-reference-field.md`](../recipes/add-reference-field.md)

## Lookup (static values / query map)

**Tables:** `ObjectLineLookup`, `ObjectLineLookupValue`

| ObjectLineLookupValue | Semantics |
|-----------------------|-----------|
| `ObjectLineLookupSourceValue` | Display label |
| `ObjectLineLookupReturnValue` | Stored value |

Recipe: [`recipes/add-lookup-field.md`](../recipes/add-lookup-field.md)

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
