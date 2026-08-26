# Object line types

`ObjectLineTypeID` (1–20) drives which **ObjectLine** columns Admin enables and which **ObjectDefaultLine** (template) capabilities apply. Spec slugs: [`data/field-type-mapping.json`](../data/field-type-mapping.json). Grammar for extended validation and Client-Math/String: [xeelo-grammar.md](xeelo-grammar.md).

**ObjectSubLine** uses the **same spec keys** and the same type IDs for every type that exists on a subgrid. SQL columns are `ObjectSubLine*` instead of `ObjectLine*` (`AttachmentStorageID` and `WebFrameTypeID` are shared names). Číselník is still `ObjectLineSource`. See [Subgrid columns](#subgrid-columns-objectsubline).

## Catalog

Slot is required when the line is **active** and the type is **not** 5, 6, 13, 16, 17.

| ID | Admin name | Spec slug | Slot |
|----|------------|-----------|------|
| 1 | Combo-box | `combobox` | yes |
| 2 | Combo-box (search) | `combobox_search` | yes |
| 3 | Text box (1 line) | `text` | yes |
| 4 | Text box (multi line) | `textarea` | yes |
| 5 | Sub-grid | `subgrid` | no |
| 6 | Empty space | `empty_space` | no |
| 7 | Check-box (Yes/No) | `checkbox` | yes |
| 8 | Date picker | `date` | yes |
| 9 | Attachment | `attachment` | yes |
| 10 | Web frame | `web_frame` | yes |
| 11 | Memo | `memo` | yes (stores **memo record ID**, not HTML) |
| 12 | Number | `number` | yes |
| 13 | Report | `report` | no |
| 14 | Combo-box (server) | `combobox_server` | yes |
| 15 | Time picker | `time` | yes |
| 16 | Description memo | `description_memo` | no |
| 17 | Attachment preview | `attachment_preview` | no |
| 18 | Button | `button` | yes |
| 19 | Radio buttons | `radio` | yes |
| 20 | Check-box (Multiselect) | `checkbox_multiselect` | yes |

Never omit **reference** on combo / radio / multi (`ObjectLineSourceID` is required in Admin). Lookup is an optional **query map** on the same field — not a substitute for the číselník.

## ObjectLine extras by type

Spec keys on `layout.tabs[].sections[].fields[]`. Existing: `precision`, `objectSub` / `objectSubId`, `saveAction`, `reference`.

| Type | Required / typical extras |
|------|---------------------------|
| `number` | `precision` required in Admin (`ObjectLineNumberPrecision` / **`ObjectSubLineNumberPrecision`**); without it a **subgrid** number does not store. `numberSeparator`, `numberMin`, `numberMax`; on-grid **total** (`onGrid.fields.<code>.isTotal`; subgrid: `subgrids.<key>.onGrid.fields.<code>.isTotal`) |
| `button` | `saveAction` required — **0 Save** (stay on the request), **1 Save & close** ([`ObjectLineButtonSaveAction.json`](../data/enums/ObjectLineButtonSaveAction.json)). Use **0** when the click should run an ObjectAction / Node.js Last. Optional `buttonMessage`; **`colorBack` / `colorFont`** = `CustomColorCode` from the site palette (Admin Color Back / Color Font; not HEX). GUI classes `xe-back-{code}` / `xe-font-{code}`. Palette: [`CustomColor.json`](../data/enums/CustomColor.json). |
| `attachment` | `attachmentStorageId` required; `ocr`, `ocrLang`, `imageResizeMax`, `mobileScan`, `mobileSignature` |
| `attachment_preview` | `previewField` (attachment field **code**) required → `ObjectLineAttPreviewObjectLineID`; optional `previewDownload` |

```yaml
- name: Update
  code: line_update
  type: button
  slot: 10
  saveAction: 0
  colorFont: white
  colorBack: blue
```

Example (preview bound to the Invoice attachment on the same object):

```yaml
- name: Invoice
  code: line_invoice
  type: attachment
  slot: 26
  attachmentStorageId: 0
- name: Preview
  code: line_preview
  type: attachment_preview
  slot: null
  previewField: line_invoice
  previewDownload: true
```

| `subgrid` | `objectSub` (spec `subgrids:` key) or `objectSubId` (existing/shared `ObjectSub`). Parent line has **no slot**. Bind template: `templates.fields.<code>.subgridTemplate` |
| `combobox`, `combobox_search`, `combobox_server`, `radio`, `checkbox_multiselect` | `reference` required; `filterField` optional (this object’s line vs source `values[].filter` or refObject `valueFilter`); combo: `isReferenceLink` |
| `text` | `textInputType` (0 Default, 1 Bar Code, 2 Location); source optional |
| `radio`, `checkbox_multiselect` | `columnNumbers` required (`ObjectLineNumberColumns`) |
| `web_frame` | `webFrameTypeId` (1 Offline file … 4 Web iFrame) |
| `description_memo` | `descMemoBorder` default **false** (omit or `false`; set `true` only when the user wants a box). `descMemoPadding` optional. Template **default is HTML** (`ObjectDefaultLineDescMemo`), not `ObjectDefaultLineValue` |
| `memo`, `report` | `height` in **px** (`ObjectLineHeight`). Omit or `0` = unlimited. Typical values 50–150, not row count. Memo **slot** = memo record ID; HTML is separate (notification `{idXXXX}`). Line conditions (`is_not_empty`, `contains`, …) see the ID, not the body — gate on text / number / button. [object-actions.md](object-actions.md#objectactioncondition) |
| `date` | stored **`dd-MM-yyyy`** (GraphQL `lines`); do not parse with `new Date()` — [graphql.md](graphql.md#date-picker-type-8) |
| Unique-capable (1, 2, 3, 4, 7, 8, 12, 14, 15) | `uniqueId` 1–4 ([`ObjectLineUnique.json`](../data/enums/ObjectLineUnique.json)) — [object-model.md](object-model.md#unique) |

## Subgrid columns (`ObjectSubLine`)

Same extras table as above, on `subgrids.<key>.layout.tabs[].sections[].fields[]`. Generator maps the spec key to `ObjectSubLine*` (e.g. `precision` → `ObjectSubLineNumberPrecision`). Combo still needs `reference`; number still needs `precision`.

**Not on a subgrid** (`ObjectSubLineType` seed has no row): **5** `subgrid`, **13** `report`, **18** `button`. Generator rejects those slugs under `subgrids:`.

| vs ObjectLine | Subgrid |
|---------------|---------|
| Slot skip | **6, 16, 17** only (5 and 13 are not in the catalog) |
| Unique | boolean `ObjectSubLineIsUnique` — not `uniqueId` 1–4; not in spec yet |
| Total | `ObjectSubLineIsTotal` on types **3 and 12** (`subgrids.<key>.onGrid.fields.<code>.isTotal`) |
| Tag | `ObjectSubLineOnGridIsTag`; Admin does not type-gate the checkbox (compile still 3/4) |
| Preview | `previewField` is another **subgrid** column code → `ObjectSubLineAttPreviewObjectSubLineID` |
| `filterField` | another **subgrid** column → `ObjectSubLineSourceFilterObjectSubLineID` |
| Lookup | same spec as ObjectLine (`lookup` + `sourceField`) on the **layout** field; binds `ObjectSubDefaultLineLookupID` / `LookupObjectSubLineID`. `sourceField` is a column in **this** objectSub |
| Client calc | `subgrids.*.templates[].fields.*.clientCalculation` / `alwaysDisabled` → `ObjectSubDefaultLine*`. `id{CODE}` → `ObjectSubLineID`. Types **1–5 and 7** only (no `focus` / `device_info`). Client-Service: same ObjectService type filter as request lines (1–2 on columns) — [object-services.md](object-services.md). `defaultValue` / `defaultFilter` / `calcDelay` / `calcConfirm` same spec keys as the request template |

## Admin canSet (ObjectLine)

**canSet\*** (Admin):

| Flag | Types |
|------|--------|
| Unique | 1, 2, 3, 4, 7, 8, 12, 14, 15 — `uniqueId` scope is object / template / requestor |
| Version history | 1, 2, 3, 4, 7, 8, 9, 10, 12, 14, 15, 19, 20 |
| Alignment | 1, 2, 3, 4, 8, 12, 14, 15 |
| Search | 1, 2, 3, 4, 7, 8, 9, 11, 12, 14, 15, 19, 20 |
| On-grid tag | 3, 4 |
| On-grid search | 3, 4, 8, 12 |
| On-grid total | **12** only (`ObjectLineOnGridIsTotal`) |
| Color | 18 |
| On-grid allowed | **not** 5, 6, 13, 16 |

## On-grid tag

Admin checkbox **Tag** (`ObjectLineOnGridIsTag`) on Object Line, On-grid group. Spec: `onGrid.fields.<code>.isTag`.

Only **text** (3) and **textarea** (4). Combo-box, date, number, checkbox, … cannot be tagged. For a picklist-like filter, use a **text** line filled by lookup or client calc — not a combo.

Tagged field **values** become finer filters on the **request grid** (Inbox / Items / Tasks). After precompile, cache SQL concatenates tagged slots into one `TAG` column (comma-separated, comma-wrapped). The User UI lists **distinct current values** as tag chips. Several selected tags are **AND** (the row must contain every selected value).

Do not put commas in tag values — split is by comma. Prefer short discrete labels (code, category), not long free text. Changing Tag requires **/publish** after OT (or `/precompile` if already deployed) so the cache SQL is rebuilt. Users can hide the tag panel (`UserFilterTabIsShowDataTag`, default on). Site setting `GridFilterShowSearchMinItems` also applies to tag chips.

Not the same as **On-grid search** (`isSearch`): that is typed search on types 3, 4, 8, 12.

Subgrid lines have the same boolean (`ObjectSubLineOnGridIsTag`); compile still uses types 3 and 4. Admin does **not** type-gate the subgrid checkbox. Spec: `subgrids.<key>.onGrid.fields.<code>.isTag`.

## On-grid total

Admin checkbox **Total** (`ObjectLineOnGridIsTotal`) on Object Line, On-grid group. Spec: `onGrid.fields.<code>.isTotal`.

Only **number** (12). After precompile, inbox grid SQL adds `TOTAL_{ObjectLineID}` (`isnull` of the slot, `'0'` when empty). Inbox **Summarization** sums those columns for the current filter and shows the **line name** + total. The field does **not** need to be on the inbox card (`allowed`); `isTotal: true` with `allowed: false` is enough.

Changing Total requires **/publish** after OT (or `/precompile` if already deployed) so the cache SQL is rebuilt.

Subgrid analog: `ObjectSubLineIsTotal` on types **3** and **12**. Spec: `subgrids.<key>.onGrid.fields.<code>.isTotal`.

## On-grid badge

Inbox cells for ordinary line types run the stored string through `xe-xeelo-badge`. Syntax:

```text
[badge:{CustomColorCode}_{text}]
```

The chip uses CSS class `.xe-badge-{code}`. `{CustomColorCode}` is a palette code from [`CustomColor.json`](../data/enums/CustomColor.json) (e.g. `blue`, `purple`, `blue-steel`); a hyphen in the code is allowed. Text is everything after the first `_` following the color until `]`.

Empty value: write `""`, not `[badge:blue_]`. Several badges in one cell: space-separated tokens (`[badge:blue_A] [badge:purple_B]`). The parser is global.

A **Server-String** calc (`ObjectDefaultLineCalculationTypeID` **53**) can fill the chip from role/status. Typical SQL (request alias `r`):

```sql
blue(dbo.fnRoleName(r.RoleID))+' '+case r.RequestStatusID
  when 2 then green(dbo.fnRequestStatusName(r.RequestStatusID))
  when 3 then red(dbo.fnRequestStatusName(r.RequestStatusID))
  when 6 then dark(dbo.fnRequestStatusName(r.RequestStatusID))
  else yellow(dbo.fnRequestStatusName(r.RequestStatusID))
end
```

Helpers `blue()` / `yellow()` / `green()` / `red()` / `dark()` write Metronic-style tokens such as `[Info_Requestor] [Warning_Draft]` / `[Success_Completed]` / `[Primary_Planned]`. Add extra `when RoleID` / `when RequestStatusID` branches when the object gains approval roles or pending statuses. Hide the line on the form (`hidden` + `alwaysDisabled`); place it on the inbox with `valueWidth: 100`. Spec/generator do **not** emit server calc — after generate, set those two `ObjectDefaultLine` columns **and** an `ObjectDefaultLineCalculationOrder` row on the OT JSON ([server calculations](#server-calculations)). Open requests: GraphQL `withRefresh: true`. Completed rows: write `lines` (`withRefresh: false`) or an update action.

**Do not put `[badge:…]` on an `isTag` line** — tag chips show the raw token. Split:

| Line | `isTag` | `allowed` | Value |
|------|---------|-----------|--------|
| Filter helpers | `true` | `false` (no inbox column; leftover placements stay hidden) | plain name |
| Display | `false` | `true` + layout | badge token(s) |

Hide the inbox column title with layout `labelType: 1` and `valueWidth: 100` ([ongrid.md](ongrid.md#cells-position-and-length)).

Combo-box cannot be `isTag`. Typical pattern: combo for editing + helper **text** lines (`alwaysDisabled`) filled by an ObjectAction from `linesFormatted.{combo}` (display name, not bind ID). Attachments, numbers, and checkboxes do not process badges.

## On-grid system lines

Inbox Role, Status, Requestor, workflow, timestamps, … are **SystemLine** columns on `ObjectLineOnGrid` (`SystemLineID`, `ObjectLineID` null) — not `ObjectLine` types. Spec: `onGrid.layouts[].placements[].columns[].systemLine` (xor `field`). Catalog: [`SystemLine.json`](../data/enums/SystemLine.json). Modules, sizes, rows `T`/`A`–`E`, and IDs: [ongrid.md](ongrid.md). YAML: [spec-format.md](../transfer/spec-format.md#ongridlayouts).

## ObjectDefaultLine capabilities

Template behaviour depends on the **line type**:

| Capability | Types |
|------------|--------|
| Server calc | all **except** 5, 6, 16, 18; report (13) has server calc **disabled** in Admin |
| Client calc | types in the client-calc map below |
| Lookup | 1, 2, 3, 7, 8, 12, 14, 15, 19, 20 |
| Default value | 1, 2, 3, 4, 7, 8, 11, 12, 14, 15, 19, 20 (`ObjectDefaultLineValue`). Spec `templates.fields.<code>.defaultValue`. Description memo (16) uses `ObjectDefaultLineDescMemo` instead — [Default value and filter](#default-value-and-filter) |
| Default filter | combo / radio / multi (`ObjectDefaultLineValueFilter`). Spec `defaultFilter` — omit unless the user asks |
| Always disabled | all **except** 6, 10, 13, 16, 17 — spec `templates.fields.<code>.alwaysDisabled` → `ObjectDefaultLineIsDisabled` |
| Hint | all except empty (6) — spec `templates.fields.<code>.hint` → `ObjectDefaultLineHint` (plain or HTML). Localized via `languageTable.templateHints`. Distinct from `description_memo` `defaultValue` (`ObjectDefaultLineDescMemo`). Subgrid: `subgrids.*.templates[].fields.*.hint` → `ObjectSubDefaultLineHint`. |
| Input mask / length / autonumber | text (3) only — autonumber bind `templates.fields.<code>.autonumber` ([object-model.md](object-model.md#autonumber)); mutually exclusive with input mask |
| Whisperer | text (3) only |
| Calc delay | text (3), textarea (4), number (12) — spec `calcDelay` (ms) on the **source** line. Omit = runtime **400**. Do not set unless the user asks |
| Calc confirm | text (3), number (12) — spec `calcConfirm` → Refresh button on the **source** line. Omit = off. Do not set unless the user asks — [Client calc delay and confirm](#client-calc-delay-and-confirm) |
| Desc memo HTML | 16 only — `ObjectDefaultLineDescMemo` is the template default; **HTML** (Admin HTML editor / `innerHTML` at runtime). Spec: `templates.fields.<code>.defaultValue` |
| Subgrid template / prefill | 5 — spec `templates.fields.<code>.subgridTemplate` → `ObjectDefaultLine.ObjectSubDefaultID` (requires `objectSub:`). Prefill (`ObjectSubPrefillID`) not in spec yet |
| Report result / graph | 13 (not when client calc is Service) |
| Save suppress | when the line has a slot |

## Validation

Catalog ([`ObjectLineValidation.json`](../data/enums/ObjectLineValidation.json)): **1 Mandatory**, **2 Optional**, **9 Extended**. New template lines default to Optional — the generator **must write `ObjectDefaultLineValidationID = 2`**, not omit the column. `NULL` makes Admin's required dropdown pick the first supported catalog value and autosave (web_frame / checkbox / desc-memo / report → 2; text / combo / number → **1 Mandatory**).

Admin filters the dropdown by type. **Mandatory is not offered** for 6, 7, 10, 13, 16, 17, 18.

**Extended (`ValidationID = 9`)** — three independent boolean expressions (empty = do not apply that axis):

| Spec | Column | When true |
|------|--------|-----------|
| `extended.hidden` | `ObjectDefaultLineValidationExtHiddenCondition` | hide |
| `extended.disabled` | `…ExtDisabledCondition` | disable |
| `extended.mandatory` | `…ExtMandatoryCondition` | required |

Extended **hidden** is available whenever validation is. **Disabled** is not offered for 10, 16. **Mandatory** condition is not offered for 7, 10, 16.

`hidden: true` compiles to condition `true`. Expressions: [xeelo-grammar.md](xeelo-grammar.md#extended-validation). Spec: `templates.fields.*.extended` — generator already compiles `id{CODE}`.

Create-form **visible/editable** is **ObjectDefaultAccess** (`templates[].access`), not these validation columns. See [object-model.md](object-model.md#create-form-access-objectdefaultaccess).

## Client calculations

IDs **1–8** (`id <= 30`). Dropdown is filtered per line type. Adhoc (`id >= 30`) only for types **1, 2, 3, 12, 14, 19, 20**. Server types **51+** use `ObjectDefaultLineCalculationTypeID`, not the client dropdown.

| ID | Name | Spec `clientCalculation.type` | Line types |
|----|------|-------------------------------|------------|
| 1 | Client-Math | `math` | 7, 1, 2, 14, 19, 20, 8, 12, 3, 4, 15 |
| 2 | Client-String | `string` | same as Math **plus** memo 11 (not report) |
| 3 | Client-Service | `service` | combo/radio/multi, date, memo, number, report, text, textarea, time |
| 4 | Client-DateAdd | `date_add` | date (8) |
| 5 | Client-DateDiff | `date_diff` | combo/radio/multi, number, text, textarea |
| 6 | Client-Focus | `focus` | report (13) |
| 7 | Client-UserInfo | `user_info` | text (3) |
| 8 | Client-DeviceInfo | `device_info` | text (3) |

Client-Service requires `ObjectServiceID` (`clientCalculation.service`). On a **report** line the Service dropdown is types **3–6**; on any other line (including **subgrid** columns) types **1–2**. Spec generates type **1** only — [object-services.md](object-services.md). Subgrid client-calc types **1–5 and 7** only — no `focus` (report) or `device_info`.

Expression language for **Math** and **String**: [xeelo-grammar.md](xeelo-grammar.md#client-math-vs-client-string). Spec stores the expression **without** the `1#` / `2#` prefix. On a subgrid, `id{CODE}` compiles to `ObjectSubLineID`.

**UserInfo** / **DeviceInfo** require `expr` as a single `{Placeholder}` (without `7#` / `8#`). Catalog: [xeelo-grammar.md](xeelo-grammar.md#client-userinfo--client-deviceinfo).

## Client calc delay and confirm

Admin labels **Calculation Delay** and **Calculation Confirm**. They sit on the **source** template line (the field others `id{…}` depend on), not on the calculated line. Same columns on `ObjectSubDefaultLine`. Spec: `templates.fields.<code>.calcDelay` / `calcConfirm` (and the same keys under `subgrids.*.templates[].fields`). **Omit both unless the user asks** — generator does not write defaults.

| Spec | Column | Runtime |
|------|--------|---------|
| omit `calcDelay` | `NULL` | debounce **400 ms** (`valueChanges`, not blur). Admin table hint still says 250 ms — ignore it |
| `calcDelay: N` (`N > 0`) | `…ClientCalcDelay` | debounce **N** ms for calc/lookup/reference. Validations still run at 400 ms when `N ≠ 400` and Confirm is off |
| omit / `false` `calcConfirm` | `0` | calcs run after the debounce |
| `calcConfirm: true` | `1` | `valueChanges` run **validations only**; user clicks **Refresh** (not a modal) for a full recalc |

Confirm Admin enable: text (3) and number (12). Delay also textarea (4). Combo has no Confirm; Refresh on combo is unique / adhoc calc only.

The Refresh button also appears without Confirm when `uniqueId > 0` or the line has an adhoc client calc (`typeID > 30`).

Client-Service (ARES, …) follows this: put delay/confirm on **IČO**, not Company name, and only when asked.

## Default value and filter

Admin **Default Value** (`ObjectDefaultLineValue` / `ObjectSubDefaultLineValue`, `nvarchar(max)`). Spec `defaultValue` — set only when the field should have a default.

| Type | Stored in |
|------|-----------|
| 1, 2, 3, 4, 7, 8, 11, 12, 14, 15, 19, 20 | `…Value` |
| description_memo (16) | `…DescMemo` (HTML) |
| 5, 6, 9, 10, 13, 17, 18 | not offered |

Filled on a **new** request when the slot is empty, and later if the field was hidden at create and `Data` is still null. Checkbox: `"0"` or `"1"`; anything else becomes `"0"` except `{id…m}` (copy a parent request line onto a subgrid column). Combo: store the **reference bind**, not the display name. A string containing `{…}` is treated as dynamic and resolved via request placeholders ([notifications.md](notifications.md#placeholders)); `{SubLineNext}` is subgrid-only. Memo `{…}` uses a separate dynamic-content path.

**Default Filter** (`…ValueFilter`, nvarchar 255): combo / radio / multi only. Restricts the reference list. Spec `defaultFilter` (plain string). Omit unless the user asks.

Same keys on subgrid templates (`ObjectSubDefaultLine*`).

## Server calculations

Catalog: [`ObjectDefaultLineCalculationType.json`](../data/enums/ObjectDefaultLineCalculationType.json) (IDs **51+**). Stored on **`ObjectDefaultLineCalculationTypeID`** + **`ObjectDefaultLineCalculation`**, not the client dropdown.

Spec/generator do **not** emit those two columns. After generate, patch the `ObjectDefaultLine` row on the OT JSON (same pattern as [on-grid badge](#on-grid-badge) Server-String **53**).

### Calculation order

Server calcs and **type-5** (subgrid) parent lines also need a row in **`ObjectDefaultLineCalculationOrder`**:

| Column | Role |
|--------|------|
| `ObjectDefaultID` | Template |
| `ObjectLineID` | Line that runs (type 5, or a line with a server calc) |
| `ObjectDefaultLineCalculationOrder` | Sequence. Typical **0, 10, 20, …** |

The calculation view treats a missing row as order **999999999**. Precompile copies into `ObjectDefaultLineCalculationCache` only when:

- the line is **type 5**, or `ObjectDefaultLineCalculationTypeID` is **51–100**, **and**
- the order is **not** `999999999`

Without an order row the calc never runs. A type-5 line missing from the list is Admin consistency **C.72** (sub-grid without calculation order). Put the type-5 parent **before** any calc that reads its rows (for example Server-SubConcat).

Spec/generator do **not** emit `ObjectDefaultLineCalculationOrder`. Patch the OT JSON after generate. Extract updates `ids.base.ObjectDefaultLineCalculationOrder` (high-water) but does not write the list into spec.

Subgrid analog: **`ObjectSubDefaultLineCalculationOrder`** for `ObjectSubDefaultLine` server calcs (same 999999999 skip).

Open requests: GraphQL `withRefresh: true`. Completed rows: write `lines` (`withRefresh: false`) or an update action — [graphql.md](graphql.md).

### Server-SubConcat (52)

Concatenates one **subgrid column** across rows of this request. Formula (after parse) must match `id{digits},id{digits}`:

```text
id{type5ObjectLineID},id{ObjectSubLineID}
```

First id = parent type-5 `ObjectLineID`. Second = `ObjectSubLineID` of the column to join. Runtime joins **formatted** cell values with **`,`** (comma, **no space**). A combo/reference column uses the combo display (for example Name (value) → `Škoda Octavia (BA-101AA),Tesla Model 3 (BB-405EE)`).

Typical pattern: hidden parent **text** (`hidden` + `alwaysDisabled`), `allowed` on parent **onGrid**, type-5 at order **0**, concat line at **10**. Recipe: [add-subgrid.md](../../recipes/add-subgrid.md#calculation-order).
