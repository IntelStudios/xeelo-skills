# Object line types

`ObjectLineTypeID` (1–20) drives which **ObjectLine** columns Admin enables and which **ObjectDefaultLine** (template) capabilities apply. Spec slugs: [`data/field-type-mapping.json`](../data/field-type-mapping.json). Grammar for extended validation and Client-Math/String: [xeelo-grammar.md](xeelo-grammar.md).

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
| 11 | Memo | `memo` | yes |
| 12 | Number | `number` | yes |
| 13 | Report | `report` | no |
| 14 | Combo-box (server) | `combobox_server` | yes |
| 15 | Time picker | `time` | yes |
| 16 | Description memo | `description_memo` | no |
| 17 | Attachment preview | `attachment_preview` | no |
| 18 | Button | `button` | yes |
| 19 | Radio buttons | `radio` | yes |
| 20 | Check-box (Multiselect) | `checkbox_multiselect` | yes |

Never put **reference** and **lookup** on the same field. Combo / radio / multi require a **reference** (`ObjectLineSourceID`) in Admin.

## ObjectLine extras by type

Spec keys on `layout.tabs[].sections[].fields[]`. Existing: `precision`, `objectSubId`, `saveAction`, `reference`.

| Type | Required / typical extras |
|------|---------------------------|
| `number` | `precision` required in Admin; `numberSeparator`, `numberMin`, `numberMax`; onGrid total |
| `button` | `saveAction` required; `buttonMessage`, `colorFont`, `colorBack`; label off |
| `attachment` | `attachmentStorageId` required; `ocr`, `ocrLang`, `imageResizeMax`, `mobileScan`, `mobileSignature` |
| `attachment_preview` | `previewField` (attachment field **code**) required; `previewDownload` |
| `subgrid` | `objectSubId` required |
| `combobox`, `combobox_search`, `combobox_server`, `radio`, `checkbox_multiselect` | `reference` required; `filterField` optional; combo: `isReferenceLink` |
| `text` | `textInputType` (0 Default, 1 Bar Code, 2 Location); source optional |
| `radio`, `checkbox_multiselect` | `columnNumbers` required (`ObjectLineNumberColumns`) |
| `web_frame` | `webFrameTypeId` (1 Offline file … 4 Web iFrame) |
| `description_memo` | `descMemoBorder` default **false** (omit or `false`; set `true` only when the user wants a box). `descMemoPadding` optional. Template **default is HTML** (`ObjectDefaultLineDescMemo`), not `ObjectDefaultLineValue` |
| `memo`, `report` | `height` |
| Unique-capable (1, 2, 3, 4, 7, 8, 12, 14, 15) | `uniqueId` ([`ObjectLineUnique.json`](../data/enums/ObjectLineUnique.json)) |

**canSet\*** (Admin):

| Flag | Types |
|------|--------|
| Unique | 1, 2, 3, 4, 7, 8, 12, 14, 15 |
| Version history | 1, 2, 3, 4, 7, 8, 9, 10, 12, 14, 15, 19, 20 |
| Alignment | 1, 2, 3, 4, 8, 12, 14, 15 |
| Search | 1, 2, 3, 4, 7, 8, 9, 11, 12, 14, 15, 19, 20 |
| On-grid tag | 3, 4 |
| On-grid search | 3, 4, 8, 12 |
| Color | 18 |
| On-grid allowed | **not** 5, 6, 13, 16 |

## ObjectDefaultLine capabilities

Template behaviour depends on the **line type**:

| Capability | Types |
|------------|--------|
| Server calc | all **except** 5, 6, 16, 18; report (13) has server calc **disabled** in Admin |
| Client calc | types in the client-calc map below |
| Lookup | 1, 2, 3, 7, 8, 12, 14, 15, 19, 20 |
| Default value | 1, 2, 3, 4, 7, 8, 11, 12, 14, 15, 19, 20 (`ObjectDefaultLineValue`) |
| Default filter | combo / radio / multi |
| Always disabled | all **except** 6, 10, 13, 16, 17 |
| Hint | all except empty (6) |
| Input mask / length / autonumber | text (3) only |
| Whisperer | text (3) only |
| Calc confirm | text (3), number (12); delay also textarea (4) |
| Desc memo HTML | 16 only — `ObjectDefaultLineDescMemo` is the template default; **HTML** (Admin HTML editor / `innerHTML` at runtime). Spec: `templates.fields.<code>.defaultValue` |
| Subgrid template / prefill | 5 |
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

Client-Service requires `ObjectServiceID`. On a **report** line, Admin filters to external report services (service types 3–6).

Expression language for **Math** and **String**: [xeelo-grammar.md](xeelo-grammar.md#client-math-vs-client-string). Spec stores the expression **without** the `1#` / `2#` prefix.

**UserInfo** / **DeviceInfo** require `expr` as a single `{Placeholder}` (without `7#` / `8#`). Catalog: [xeelo-grammar.md](xeelo-grammar.md#client-userinfo--client-deviceinfo).
