# Field types in User UI (first wave)

Map spec `type` / ObjectLine type to how to fill the **open request form**. Catalog: [object-line-types.md](../../docs/entities/object-line-types.md).

Use the **visible label** (and tab/section) from the form. Spec `code` is not shown as the input name.

## Fill in the first wave

| Spec type | What to do |
|-----------|------------|
| `text` | Click the one-line input, type the value, leave the field (so calculations can run). |
| `number` | Same, with a numeric value that respects min/max/precision if the UI rejects the input. |
| `combobox`, `combobox_search`, `combobox_server` | Open the combo, pick the option whose **value/label** the user named (or the only sensible match). Search combos: type a filter then pick. Combo always has a reference (číselník); lookup may also fill another field — wait, do not fight it. |

After each fill, wait briefly if the field has Client-Service / calc (spinner or value change).

## Stop (unsupported in the first wave)

Name the field and type, then stop. Do not improvise file uploads or rich editors.

| Spec type | Why |
|-----------|-----|
| `radio`, `checkbox`, `checkbox_multiselect` | Extra clicks / multi-select |
| `textarea`, `memo`, `description_memo` | Multi-line / HTML editors |
| `date`, `time` | Date/time pickers |
| `attachment`, `attachment_preview` | File store |
| `subgrid` | Embedded grid (add-row modal) |
| `web_frame`, `report`, `empty_space`, `button` | Not typed values (`button` is Save-like — not a fill target) |

Required field in this table → fail the fill-save step.
