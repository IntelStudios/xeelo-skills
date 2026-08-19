# Recipe: Add Reference Field (Combo-box)

Add a combo-box whose values come from an **ObjectLineSource** (reference / číselník), not a static lookup.

## When to use

Task mentions: picklist, reference list, user list, company list, values from another object, dynamic dropdown from requests.

**Not** for static fixed options — use [`add-lookup-field.md`](add-lookup-field.md) (lookup / dotazovací mapa).

## Reference vs lookup

| | Reference | Lookup |
|---|-----------|--------|
| Spec | `field.reference` | `field.lookup` |
| Bind | `ObjectLine.ObjectLineSourceID` | `ObjectDefaultLine.ObjectDefaultLineLookupID` |
| Meaning | Číselník (picklist source) | Dotazovací mapa podle jiného pole |

Never both on the same field.

New `sources.*` (values / refObject) always set **`styleId: 4`** (`ObjectLineSourceStyle` = Value). Other styles only when asked. System sources (`reference.sourceId`) keep their existing style.

| `styleId` | Name | Display |
|-----------|------|---------|
| 1 | Name | label |
| 2 | Bind - name | bind - label |
| 3 | Name (value) | label (bind) |
| **4** | **Value** | **stored value (default)** |

## Variant 1: System reference (site-preexisting)

Use when the site already has a system source (User List, Company List, …). Only bind the field — do not emit `ObjectLineSource` rows.

```yaml
fields:
  - name: Type
    code: TYPE
    type: combobox
    slot: 3
    reference:
      sourceId: 1    # site ID from ids.byTable.ObjectLineSource
```

## Variant 2: Fixed values (ObjectLineSourceValue)

Define a custom table-type source with explicit options:

```yaml
sources:
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

layout:
  tabs:
    - name: General
      sections:
        - name: Details
          fields:
            - name: Color
              type: combobox
              reference:
                source: profile_colors
```

Tables emitted: `ObjectLineSource`, `ObjectLineSourceValue`, edge `ObjectLine → ObjectLineSource`.

## Variant 3: ReferenceObject (dynamic from requests)

Values computed at runtime from requests of another object:

```yaml
sources:
  cars_picker:
    name: Cars picker
    typeId: 1
    styleId: 4
    refObject:
      name: Cars Ref
      objectId: 6097
      requestType: all    # all | completed | in-progress
      lines:
        value: line_12301_id
        valueName: line_12302_name
        valueBind: line_12303_code

fields:
  - name: Car
    type: combobox
    reference:
      source: cars_picker
```

Line codes in `refObject.lines` refer to fields on the **referenced** object. Put their line IDs in `ids.explicit.refObjectLines` when generating greenfield.

Tables emitted: `ObjectLineSource`, `ObjectLineSourceRefObject`.

## Optional filter

```yaml
reference:
  sourceId: 16
  filterField: COMPANY_FIELD_CODE   # → ObjectLineSourceFilterObjectLineID
```
