# Recipe: Add Lookup Field (Combo-box)

Add a static-value combo-box to an **existing** object.

## When to use

Task mentions: dropdown, select, enum, choice list, typ (type), category with fixed options.

## Spec fragment

```yaml
fields:
  - name: Status
    code: STATUS
    type: combobox
    slot: 4          # new unique slot on object
    width: 50
    mandatory: false
    lookup:
      name: Status Options
      values:
        - { label: Open, value: OPEN }
        - { label: Closed, value: CLOSED }
```

## Tables to emit

1. **ObjectLine** — new line row (`ObjectLineTypeID=1`)
2. **ObjectLineLookup** — new lookup definition
3. **ObjectLineLookupValue** — one row per option
4. **ObjectDefaultLine** — link line to lookup via `ObjectDefaultLineLookupID`

If object already has `ObjectDefault`, add template line only. If not, create full template chain (see [`create-object.md`](create-object.md)).

## Lookup value columns

| Column | Value |
|--------|-------|
| `ObjectLineLookupSourceValue` | Display text in UI |
| `ObjectLineLookupReturnValue` | Stored value |
| `ObjectLineLookupFilterValue` | Optional filter (usually null) |

## Reference types (not this recipe)

Combo-box fields use **lookup** for static lists and dotazovací mapy. For **reference** (ObjectLineSource / číselník), see [`add-reference-field.md`](add-reference-field.md).

Other source types (out of scope here):

- **Reference External** — SQL/external source (`ObjectLineSourceRefExternal`)
- **Combo-box (server)** — server-side search (type ID 14)

Static lists use **ObjectLineLookup** + **ObjectLineLookupValue** on the **template line** only.

## Hints

From [`data/table-hints.json`](../data/table-hints.json) — lookup fields configured on template line as **Source** (`ObjectDefaultLineLookupID` in Admin UI).
