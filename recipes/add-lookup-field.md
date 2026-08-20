# Recipe: Add Lookup Field (query map)

Fill a field from **another field** using an `ObjectLineLookup` map (dotazovací mapa). Not a picklist — combo / radio / multi still need a **reference**.

## When to use

Task mentions: derive / map value from another line, query map, lookup that recalculates when X changes, optional extra filter line.

Admin types that allow lookup: combo, combo search/server, text, checkbox, date, number, time, radio, multi.

## Shared map + field binding

Put the map in `spec/lookups.yaml`. The field only names the map and the trigger line(s).

```yaml
# spec/lookups.yaml
lookups:
  priority_by_kind:
    name: Priority by kind
    values:
      - { source: demo, return: LOW }
      - { source: full, return: HIGH }

# spec/references.yaml  — required if the target is a combo
references:
  ks_priority:
    name: Priority
    typeId: 1
    styleId: 4
    values:
      - { value: LOW, label: Low }
      - { value: MED, label: Medium }
      - { value: HIGH, label: High }

# field:
- name: Priority
  code: ks_priority
  type: combobox
  slot: 13
  reference:
    reference: ks_priority
  lookup:
    lookup: priority_by_kind
    sourceField: ks_kind          # required — Admin Source field
    # filterField: ks_flag        # optional exact Filter
```

When the user changes `ks_kind`, lookup matches `source` against that value and writes `return` into Priority. `return` must exist in the reference (here LOW / HIGH). `ObjectLineLookupSourceValue` is **not** a combo label.

## Text field (no reference)

```yaml
lookups:
  title_from_kind:
    name: Title from kind
    values:
      - { source: demo, return: "Demo request" }
      - { source: full, return: "Full request" }

# field:
- name: Title
  code: ks_title
  type: text
  lookup:
    lookup: title_from_kind
    sourceField: ks_kind
```

## Filter

`values[].filter` is exact equality with the Filter field (`ObjectDefaultLineLookupFilterObjectLineID`). Empty filter on the template line uses rows with `FilterValue` NULL. This is **not** comma-split; comma lists belong to **reference** `ObjectLineSourceValueFilter`.

## Tables to emit

1. **ObjectLineLookup** + **ObjectLineLookupValue** (once per map key)
2. **ObjectDefaultLine** — `ObjectDefaultLineLookupID`, `…LookupObjectLineID`, optional `…LookupFilterObjectLineID`
3. Combo: **ObjectLineSource** as usual (`reference`)

Same `lookups:` key → one `ObjectLineLookup` shared by fields.

Inline `lookup.values` on the field still works for a one-off map.

## Hints

Admin template group **Lookup**: Source (`ObjectDefaultLineLookupID`), Source field, Filter.
