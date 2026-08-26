# Recipe: Add subgrid

Embedded repeatable table on a parent **type 5** line (`ObjectSub` via `ObjectLine.ObjectSubID`). Own tabs, sections, columns, and templates.

Not a request. Rows live under the parent request (no own workflow). Details: [object-model.md](../docs/entities/object-model.md#subgrid).

## When to use

Task mentions: line items, sub-table, nested rows, ObjectSub, sub-grid.

Default is **1:1** (tree in this object’s `spec/subgrids.yaml`). Sharing one `ObjectSub` across objects is uncommon — second object uses `objectSubId:` only.

## Spec

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
        name: Default
        isDefault: true
        fields:
          DESC:
            mandatory: true
          TOTAL:
            alwaysDisabled: true
            clientCalculation:
              type: math
              expr: id{QTY} * id{AMOUNT}

    onGrid:
      fields:
        DESC: { allowed: true, isSearch: true }
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

# layout — parent type 5, no slot
- name: Lines
  code: LINES
  type: subgrid
  width: 100
  order: 1
  objectSub: invoice_lines

# spec/templates.yaml — which ObjectSubDefault new rows use
templates:
  - key: default
    name: Default
    isDefault: true
    fields:
      LINES:
        subgridTemplate: default
```

**Share** an existing site subgrid (no new tree):

```yaml
- name: Lines
  code: LINES
  type: subgrid
  width: 100
  order: 1
  objectSubId: 4242
```

## Access

A missing access row hides the widget **and** the add/edit-row modal columns. Object Transfer does **not** run Admin access refresh.

Emit **both**:

1. **Create** — `templates[].access` on the parent type-5 line (`visible: true`, `editable: true`). Skip this and a **new** request has no `ObjectDefaultAccess` row for the widget.
2. **Every workflow step** that should show it — `workflow.steps[].access`. `editable: true` where users add rows; at least `visible: true` on the others (Review / Completed). Skip a step and existing requests on that step hide the subgrid.

The generator copies that parent access onto every `ObjectSubLine` (modal fields) unless you override a column. A widget-only row is not enough — without column rows the modal is empty.

`access[].field` is the **parent** type-5 line. Optional `access[].subline` is the column **code** in that `objectSub` tree (`sublineId` is the numeric Orig. ID). Shared `ObjectSub` still has **per-object** access because `ObjectLineID` differs. `objectSubId` (no tree in spec) does not auto-expand columns — list `sublineId` yourself.

```yaml
# spec/templates.yaml
templates:
  - key: default
    fields:
      LINES:
        subgridTemplate: default
    access:
      - field: LINES
        visible: true
        editable: true

# spec/workflow.yaml — every step that should show the grid
workflow:
  steps:
    - name: Draft
      access:
        - field: LINES
          editable: true
    - name: Review
      access:
        - field: LINES
          visible: true
    - name: Completed
      access:
        - field: LINES
          visible: true
```

After `/download-db`, extract drops refresh-default **widget** rows (create: both yes; step: visible yes, editable no) but **keeps** column rows (`ObjectSubLineID` set). Later loops do not re-list widget defaults unless flags change. Override one column:

```yaml
access:
  - field: LINES
    subline: DESC
    visible: false
```

## onGrid

Same two layers as request inbox `onGrid`, on the **subgrid table** (not the parent inbox):

1. `subgrids.<key>.onGrid.fields` — `ObjectSubLine` flags (`allowed`, `isSearch`, `isTag`, `isTotal`)
2. `subgrids.<key>.onGrid.layouts` — `ObjectSubLineOnGrid` placement (`size` × Grid/Table × `module`). Columns are `field:` only (no `systemLine`).

Always add this when creating a subgrid. `layout.fields` is the add/edit-row **form**; `onGrid` is which columns appear in the **table of rows**. Default `ObjectSubLineOnGridIsAllowed` is false.

`isTotal` on a subgrid is `ObjectSubLineIsTotal` (types **3 and 12**). `isTag` is `ObjectSubLineOnGridIsTag` (compile types 3 and 4). After deploy, **/publish** so cache SQL is rebuilt.

## Calculation order

The type-5 parent **must** have an **`ObjectDefaultLineCalculationOrder`** row on the template (typical order **0**, then **10**, **20**, …). Without it Admin reports **C.72** (sub-grid without calculation order) and request refresh skips the subgrid.

Spec/generator do **not** emit this table. After generate, patch the OT JSON:

```json
{
  "ObjectDefaultLineCalculationOrder": [
    {
      "ObjectDefaultLineCalculationOrderID": 40,
      "ObjectDefaultID": 12,
      "ObjectLineID": 80,
      "ObjectDefaultLineCalculationOrder": 0,
      "IsActive": true
    }
  ]
}
```

`ObjectDefaultLineCalculationOrderID` is the next Orig. ID (`ids.base.ObjectDefaultLineCalculationOrder` + 1). `ObjectDefaultID` / `ObjectLineID` are the template and type-5 line from env.

**Inbox list of a subgrid combo (or other column):** hidden parent **text** + server calc **Server-SubConcat (52)** `id{type5ObjectLineID},id{ObjectSubLineID}`. Put that line later in the same order list (for example type-5 at 0, concat at 10). Joins formatted values with `,` (no space). Spec does not emit the calc either — patch `ObjectDefaultLine` the same way as Server-String **53**. Details: [object-line-types.md](../docs/entities/object-line-types.md#server-subconcat-52).

## Unique / autonumber / Generate

Several unique **subgrid** columns are a **composite AND** within that parent request (`ObjectSubLineIsUnique`) — spec does not emit that yet. Request unique is per-field `uniqueId` 1–4. Autonumber on a subgrid **text** column: same `autonumbers:` catalog, bind on `subgrids.*.templates[].fields.*.autonumber`.

**Generate** on the `ObjectSub` plus **Multiselect** on a combobox column creates one sub-row per selected číselník value. Not type 20 `checkbox_multiselect`. Not in spec yet.

## Tables to emit

1. **ObjectSub** (+ Tab / Section / Line)
2. **ObjectSubDefault** + **ObjectSubDefaultLine**
3. **ObjectLine** type 5 — `ObjectSubID`
4. **ObjectDefaultLine** — `ObjectSubDefaultID` when `subgridTemplate` is set
5. **ObjectDefaultAccess** + **WorkflowStepAccess** — parent type-5 line **and** each ObjectSubLine (modal columns). Generator expands parent access onto columns when `objectSub:` is in spec.
6. **ObjectSubLineOnGrid** — from `subgrids.<key>.onGrid.layouts` (flags on `ObjectSubLine` from `onGrid.fields`)
7. **ObjectDefaultLineCalculationOrder** — type-5 parent (and any parent server calc that reads the subgrid). Not generated from spec; patch after generate.
8. Edges: `ObjectLine → ObjectSub`, `ObjectSub → ObjectSubLine` / `ObjectSubDefault`, `ObjectSubLine → ObjectSubLineOnGrid`, `ObjectSubDefaultLine → ObjectLineAutoNumber` when `autonumber` is set, `ObjectSubDefaultLine → ObjectLineLookup` when `lookup` is set

`objectSubId` without `subgrids:` emits only the parent FK.

## Hints

Parent type 5 has no slot and is not on the request inbox grid. `ObjectSubWidth` is the **add/edit-row modal** width (percent). Default **80**. Admin allows 50–100. More columns go in extra **tabs / sections** or stacked fields (`width: 100`) — do not bump the modal past 80 just because the tree grew. Label of the type-5 line stays in the SubGrid header (`IsHorizontal` does not move it). GraphQL names come from `ObjectSubCode`.

**Type extras** are the same spec keys as ObjectLine (`precision`, `reference`, `attachmentStorageId`, `previewField`, `columnNumbers`, …). SQL is `ObjectSubLine*`. Number needs `precision` (slot alone does not store). Combo/radio/multi need `reference`. Lookup (`lookup` + `sourceField` on another **subgrid** column) and client-calc (`templates[].fields.*.clientCalculation`, `id{CODE}` → `ObjectSubLineID`) sit on `ObjectSubDefaultLine`. Same opt-in keys as the request template: `defaultValue`, `defaultFilter`, `calcDelay`, `calcConfirm` (do not set delay/confirm unless asked). No nested `subgrid`, `report`, or `button`. Czech labels: `languageTable.subgrids.<key>`. [object-line-types.md](../docs/entities/object-line-types.md#subgrid-columns-objectsubline).
