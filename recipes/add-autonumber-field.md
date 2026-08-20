# Recipe: Add autonumber field (request identifier)

Use a **text** line as a unique request identifier: bind a site **autonumber** (sequence) on the template line and set Unique on the ObjectLine.

Not a field type — autonumber is a catalog (`ObjectLineAutoNumber`). Unique is a **level** on the line (`uniqueId`).

## When to use

Task mentions: request number, sequence, unique identifier, autonumber, unique on the line.

## Spec

```yaml
# spec/autonumbers.yaml
autonumbers:
  request_no:
    description: Request number
    format: REQ####
    next: 1
    # resetTypeId: 1   # optional Yearly

# layout field — unique is on ObjectLine
- name: Request number
  code: REQUEST_NO
  type: text
  slot: 1
  uniqueId: 1          # 1 Object, 2 Object/Template, 3 Object/Requestor, 4 all three

# spec/templates.yaml — bind + usually not user-edited
templates:
  - key: default
    name: Default
    isDefault: true
    fields:
      REQUEST_NO:
        autonumber: request_no
        alwaysDisabled: true
```

On a **single** default template you may set `autonumber: request_no` on the layout field instead of `templates.yaml`.

`format`: one contiguous `#` run (zero-padded digits). Prefix/suffix around it. Optional `YYYY` / `YY` / `MM` / `DD` after generate. Do not put literals between hashes (`##-##` is one span).

Insert stores the format (still with `#`) as a placeholder; refresh generates the next number. Same autonumber key → one shared counter.

## Unique

`uniqueId` on types 1, 2, 3, 4, 7, 8, 12, 14, 15. Empty values are not checked; only **submitted** requests.

Several unique **request** lines are each unique on their own (not a composite tuple). For a request identifier use **one** autonumber field. Several unique **subgrid** lines are a composite key — spec does not emit that yet.

## Tables to emit

1. **ObjectLineAutoNumber** (once per `autonumbers:` key)
2. **ObjectLine** — `ObjectLineUniqueID` + `ObjectLineIsUnique = 1`
3. **ObjectDefaultLine** — `ObjectDefaultLineAutoNumberID`
4. Edge: `ObjectDefaultLine → ObjectLineAutoNumber`

## Hints

Admin / Objects / Autonumber defines the catalog. Template line group Autonumber picks it. Unique is on Object Line (not the template). Text only; no input mask on the same line.

Details: [object-model.md](../docs/entities/object-model.md#autonumber).
