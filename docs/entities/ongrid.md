# Inbox and subgrid onGrid

Request inbox cards and subgrid lists are **onGrid**: flags on the line, plus one **placement** row per layout variant. Spec YAML: [`spec-format.md`](../transfer/spec-format.md#ongrid) (inbox) and [`spec-format.md`](../transfer/spec-format.md#subgrids-specsubgridsyaml) (`subgrids.<key>.onGrid`). Type gates (tag / search / total / badge): [object-line-types.md](object-line-types.md). Recipe: [create-object.md](../../recipes/create-object.md).

SQL columns can store any Size / Type / Module string. **Precompile only builds cache slots listed below.** Do not spec combinations outside that catalog — they will not appear in User GUI cache.

## Two layers

| Layer | Object (inbox) | Subgrid |
|-------|----------------|---------|
| Flags | `ObjectLine` (`ObjectLineOnGridIsAllowed`, `Name`, `IsTag`, `IsSearch`, `IsTotal`) | `ObjectSubLine` (`ObjectSubLineOnGridIsAllowed`, `Name`, `IsTag`; search/total are `ObjectSubLineIsSearch` / `ObjectSubLineIsTotal`) |
| Placement | `ObjectLineOnGrid` | `ObjectSubLineOnGrid` |

Spec: `onGrid.fields.<code>` (flags) and `onGrid.layouts[]` (placements). `allowed: true` without a layout lists the field but does not paint it. A layout without `allowed` is dropped at extract / compile (`ObjectLineOnGridIsAllowed = 1`).

After changing tag / search / total flags, **/publish** (or `/precompile`) so cache SQL is rebuilt.

## Layout axes

Each `ObjectLineOnGrid` / `ObjectSubLineOnGrid` row is one triple:

- **Module** — User GUI surface. Spec keys (Admin label): `Items` (Items), `Tasks` (Tasks), `Relation` (Relation), `RelationMap` (Relation Map), `MobileItems` (Mobile Items), `MobileTasks` (Mobile Tasks)
- **Type** — `Grid` or `Table`
- **Size** — `Large` (desktop), `Medium` (tablet), `Small` (phone) where the catalog allows it

**Grid** stacks placement letters `T`, `A`–`E` as visual rows. **Table** always paints **one** visual row; those letters do not wrap — extra columns scroll horizontally.

## ObjectLine catalog (request inbox)

Seventeen cache slots:

**Items** (inbox of requests)

- Grid: Large, Medium, Small
- Table: Large, Medium, Small

**Tasks**

- Grid: Large, Medium, Small
- Table: Large, Medium, Small

**Relation** (request relations)

- Grid: Large only
- Table: Large only

**Relation Map**

- Grid: Large only
- Table: none

**Mobile Items**

- Grid: Small only
- Table: none

**Mobile Tasks**

- Grid: Small only
- Table: none

## ObjectSubLine catalog (subgrid)

Three cache slots. No SystemLine columns (`ObjectSubLineOnGrid` has only `ObjectSubLineID`).

**Items**

- Grid: Large
- Table: Large

**Mobile Items**

- Grid: Large only (not Small; not Table)

No Tasks / Relation / Relation Map / Mobile Tasks slots for subgrid.

Spec: `subgrids.<key>.onGrid` (`fields` + `layouts`) — [add-subgrid.md](../../recipes/add-subgrid.md#ongrid). Schema: [`ObjectSubLineOnGrid.json`](../schemas/ObjectSubLineOnGrid.json) (no `ObjectID` or `SystemLineID`; `ObjectSubLineID` is required).

## Default for a new object

Write **seven** `onGrid.layouts` (generator does not invent them if omitted):

1. Items / Grid / Large
2. Items / Grid / Medium
3. Items / Grid / Small
4. Items / Table / Large
5. Items / Table / Medium
6. Items / Table / Small
7. Mobile Items / Grid / Small

Do **not** copy Large placements onto Medium or Small for **Grid or Table**. The surface is about **half as wide** each step down, so the same one-row percents are too cramped. Put fewer columns per letter and extra `T`/`A`–`E` rows. Lengths still sum to **100 on each letter**.

- **Large** — one `T` row is fine when columns sum to 100
- **Medium** — treat as ~½ Large: about **half as many columns per row** (typically `T` + `A`)
- **Small** — treat as ~½ Medium: wrap again (typically `T` + `A` + `B`, or a full-width title on `T`)
- **Mobile Items Grid Small** — same wrap as Items Small. Consecutive letters; never skip to `B` and leave `A` empty

**Grid** stacks those letters into visual rows. **Table** in the User GUI is still one spreadsheet row of columns (`row` does not wrap on screen); spec the same T/A/B grouping so Medium/Small Table match Grid. Short fields (number, date) may share a Small letter; a long title usually takes the full `T` row.

Do **not** spec Tasks, Relation, Relation Map, or Mobile Tasks unless the user wants a different layout. Tasks and Relation fall back (below). **Mobile Items does not fall back to desktop Items** — omit layout 7 and the phone inbox is empty.

## Failover (User GUI)

Not a spec feature. If a requested slot has no placements:

- Items / Tasks: missing Small → Medium → Large; missing Table → Grid at the same size
- Tasks with no own layout → Items at the same size and type
- Mobile Tasks with no layout → Mobile Items; if that is empty too, stay empty
- Relation Table → Relation Grid Large, then Items / Grid / Large
- Relation Map → Items / Grid / Large

## Rows T, A, B, C, D, E

`placements[].row` is `ObjectLineOnGridRow` / `ObjectSubLineOnGridRow` (`T`, `A`–`E`). YAML order does not matter; the letter does.

Paint order on **Grid**:

1. **T** — title row (distinct CSS)
2. **A** — first body row, directly under T
3. **B** — third visual row
4. **C**, **D**, **E** — further body rows

**T + A** is two stacked rows with no gap (typical phone card). **T + B** skips A; the runtime fills A with an empty 100% spacer. There is no KB rule to use T + B. **B is not “bottom”.**

On **Table**, letters do **not** stack in the User GUI (one line of columns). Still spec Medium/Small Table with the same wrap as Grid so grouping matches.

## Cells: position and length

- `position`: start in percent (**0–99**)
- `length`: width in percent (**1–100**); lengths on one `row` should sum to **100**
- Interval is half-open: `position: 0`, `length: 12` occupies 0–11; the next column starts at **12**
- Overlap: next `position` &lt; previous `position + length`

`labelType`: **1** Horizontal (default), **2** Vertical. Do not spec SQL `0` (None); Admin does not offer it.

`valueWidth`: `0` = auto. **`100` + Horizontal** hides the column label (badges / Role / Status chips).

Each column is **`field` xor `systemLine`** on ObjectLineOnGrid. System lines: [`SystemLine.json`](../enums/SystemLine.json) (`role` 40, `status` 50, `requestor` 80, …). Explicit ID `{size}/{type}/{module}/sys:{code}`. Field key `{size}/{type}/{module}/{code}`.

Combo-box (**types 1, 2, 14**) may be `allowed` and placed; inbox shows the numberedník name, not the bind id. Combo **cannot** be `isTag` or on-grid `isSearch`. On-grid allowed is **not** types 5, 6, 13, 16 (subgrid, empty, report, description memo).

## Example

Large **Grid** and **Table** one `T` row; Medium wraps to `T`+`A`; Small wraps again (`T`+`A`+`B`). Mobile Items follows Small Grid.

```yaml
onGrid:
  fields:
    REQ_NO:
      allowed: true
      name: No.
      isSearch: true
    TITLE:
      allowed: true
      name: Title
      isSearch: true
    PRIORITY:
      allowed: true
      name: Priority
    DATE:
      allowed: true
      name: Date
      isSearch: true
  layouts:
  - size: Large
    type: Grid
    module: Items
    placements:
    - row: T
      columns:
      - { field: REQ_NO, position: 0, length: 12, valueWidth: 0, labelType: 1 }
      - { field: TITLE, position: 12, length: 48, valueWidth: 0, labelType: 1 }
      - { field: PRIORITY, position: 60, length: 20, valueWidth: 0, labelType: 1 }
      - { field: DATE, position: 80, length: 20, valueWidth: 0, labelType: 1 }
  - size: Medium
    type: Grid
    module: Items
    placements:
    - row: T
      columns:
      - { field: REQ_NO, position: 0, length: 25, valueWidth: 0, labelType: 1 }
      - { field: TITLE, position: 25, length: 75, valueWidth: 0, labelType: 1 }
    - row: A
      columns:
      - { field: PRIORITY, position: 0, length: 50, valueWidth: 0, labelType: 1 }
      - { field: DATE, position: 50, length: 50, valueWidth: 0, labelType: 1 }
  - size: Small
    type: Grid
    module: Items
    placements:
    - row: T
      columns:
      - { field: TITLE, position: 0, length: 100, valueWidth: 0, labelType: 1 }
    - row: A
      columns:
      - { field: REQ_NO, position: 0, length: 40, valueWidth: 0, labelType: 1 }
      - { field: DATE, position: 40, length: 60, valueWidth: 0, labelType: 1 }
    - row: B
      columns:
      - { field: PRIORITY, position: 0, length: 100, valueWidth: 0, labelType: 1 }
  - size: Large
    type: Table
    module: Items
    placements:
    - row: T
      columns:
      - { field: REQ_NO, position: 0, length: 12, valueWidth: 0, labelType: 1 }
      - { field: TITLE, position: 12, length: 48, valueWidth: 0, labelType: 1 }
      - { field: PRIORITY, position: 60, length: 20, valueWidth: 0, labelType: 1 }
      - { field: DATE, position: 80, length: 20, valueWidth: 0, labelType: 1 }
  - size: Medium
    type: Table
    module: Items
    placements:
    - row: T
      columns:
      - { field: REQ_NO, position: 0, length: 25, valueWidth: 0, labelType: 1 }
      - { field: TITLE, position: 25, length: 75, valueWidth: 0, labelType: 1 }
    - row: A
      columns:
      - { field: PRIORITY, position: 0, length: 50, valueWidth: 0, labelType: 1 }
      - { field: DATE, position: 50, length: 50, valueWidth: 0, labelType: 1 }
  - size: Small
    type: Table
    module: Items
    placements:
    - row: T
      columns:
      - { field: TITLE, position: 0, length: 100, valueWidth: 0, labelType: 1 }
    - row: A
      columns:
      - { field: REQ_NO, position: 0, length: 40, valueWidth: 0, labelType: 1 }
      - { field: DATE, position: 40, length: 60, valueWidth: 0, labelType: 1 }
    - row: B
      columns:
      - { field: PRIORITY, position: 0, length: 100, valueWidth: 0, labelType: 1 }
  - size: Small
    type: Grid
    module: MobileItems
    placements:
    - row: T
      columns:
      - { field: TITLE, position: 0, length: 100, valueWidth: 0, labelType: 1 }
    - row: A
      columns:
      - { field: REQ_NO, position: 0, length: 40, valueWidth: 0, labelType: 1 }
      - { field: DATE, position: 40, length: 60, valueWidth: 0, labelType: 1 }
    - row: B
      columns:
      - { field: PRIORITY, position: 0, length: 100, valueWidth: 0, labelType: 1 }
```

Inbox column titles stay English unless the site asks for `languageTable.lines.<code>.onGrid`.
