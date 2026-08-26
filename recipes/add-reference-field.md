# Recipe: Add Reference Field (Combo-box)

Add a combo-box whose values come from an **ObjectLineSource** (reference / číselník).

## When to use

Task mentions: picklist, reference list, user list, company list, values from another object, dynamic dropdown from requests.

Static **fixed options** still use a **reference** (`references.*.values[]`). A **lookup** is a query map on top of a field — see [`add-lookup-field.md`](add-lookup-field.md). Combo / radio / multi always need a reference.

## Reference vs lookup

| | Reference | Lookup |
|---|-----------|--------|
| Spec file | `spec/references.yaml` | `spec/lookups.yaml` |
| Spec | `field.reference.reference` / `referenceId` | `field.lookup.lookup` + `sourceField` |
| Bind | `ObjectLine.ObjectLineSourceID` | `ObjectDefaultLine.ObjectDefaultLineLookupID` |
| Meaning | Číselník (picklist) | Dotazovací mapa podle jiného pole |

Both on the same combo is allowed: reference = options, lookup = which option to set when another field changes.

New `references.*` (values / refObject) always set **`styleId: 4`** (`ObjectLineSourceStyle` = Value). Other styles only when asked. System lists (`reference.referenceId`) keep their existing style.

| `styleId` | Name | Display |
|-----------|------|---------|
| 1 | Name | label |
| 2 | Bind - name | bind - label |
| 3 | Name (value) | label (bind) |
| **4** | **Value** | **stored value (default)** |

## Variant 1: System reference (site-preexisting)

Use when the site already has a system list (User List, Company List, …). Only bind the field — do not emit `ObjectLineSource` rows.

```yaml
fields:
  - name: Type
    code: TYPE
    type: combobox
    width: 50
    order: 1
    slot: 3
    reference:
      referenceId: 1    # site ID from ids.byTable.ObjectLineSource
```

## Variant 2: Fixed values (ObjectLineSourceValue)

```yaml
# spec/references.yaml
references:
  profile_colors:
    name: Profile colors
    typeId: 1
    styleId: 4
    values:
      - value: "3"
        label: Modrá
        bind: "3"
      - value: "4"
        label: Černá
        bind: "4"

# field:
- name: Color
  type: combobox
  reference:
    reference: profile_colors
```

Tables emitted: `ObjectLineSource`, `ObjectLineSourceValue`, edge `ObjectLine → ObjectLineSource`.

## Variant 3: ReferenceObject (dynamic from requests)

```yaml
references:
  cars_picker:
    name: Cars picker
    typeId: 1
    styleId: 4
    refObject:
      name: Cars Ref
      objectId: 6097
      requestType: all    # Admin Request Type: All | Only completed | Only inprogress
      lines:
        value: line_12301_id
        valueName: line_12302_name
        valueBind: line_12303_code

fields:
  - name: Car
    type: combobox
    reference:
      reference: cars_picker
```

Line codes in `refObject.lines` refer to fields on the **referenced** object. Put their line IDs in `ids.explicit.refObjectLines` when generating greenfield.

| `refObject.lines.*` | Column | Role |
|---------------------|--------|------|
| `value` | `ValueObjectLineID` | Stored option value |
| `valueName` | `ValueNameObjectLineID` | Display name (`styleId: 1`) |
| `valueBind` | `ValueBindObjectLineID` | Bind / match key |
| `valueFilter` | `ValueFilterObjectLineID` | Value compared to the consuming combo’s `filterField` |
| `valueOrder` | `ValueOrderObjectLineID` | Sort |

`refObject.requestType` (`ObjectLineSourceRefObjectRequestTypeID`; default `all`). Not Create/Update `RequestTypeID`. Enum: [`ObjectLineSourceRefObjectRequestType.json`](../data/enums/ObjectLineSourceRefObjectRequestType.json).

| ID | Admin | Spec | Combo options |
|----|-------|------|----------------|
| 0 | All | `all` (default) | last version of each request |
| 1 | Only completed | `completed` | last version only when it is completed |
| 2 | Only inprogress | `in-progress` | last version only when it is not completed |

The generator also writes deprecated `ObjectLineSourceRefObjectIsOnlyCompleted` (`1` iff `completed`); runtime uses Request Type.

Tables emitted: `ObjectLineSource`, `ObjectLineSourceRefObject`.

## Optional filter

The consuming combo/radio/multi sets `reference.filterField` → `ObjectLine.ObjectLineSourceFilterObjectLineID` (a line **on this object**). What it is compared against depends on the reference mode.

### Fixed values (comma-split)

```yaml
reference:
  reference: colors
  filterField: COMPANY_FIELD_CODE
```

`values[].filter` → `ObjectLineSourceValueFilter` is comma-separated. Every current filter-field value must appear in that list (intersection).

### refObject (line on the other object)

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
        valueFilter: line_applicability   # field on Payment label

fields:
  - name: Label
    type: combobox
    reference:
      reference: payment_label
      filterField: DIRECTION              # field on this object
```

Runtime keeps options whose `valueFilter` line equals the current `filterField` value. Use the **same stored strings** on both sides (e.g. Direction text `Příjem` / `Výdej` and Applicability combo binds). Distinct from lookup `filterField` (exact string on `ObjectLineLookupFilterValue`).
