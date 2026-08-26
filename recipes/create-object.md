# Recipe: Create Object

Minimal path to a usable Xeelo object — outputs **Object Transfer** JSON (not DB transfer).

## Prerequisites

- Define **roles** and **statuses** in spec (or rely on minimal defaults); set `ids.explicit.roles` / `statuses` after site sync
- **WorkflowStepActionStyle** ID 1 must exist on target site (referenced by ID, not emitted)

Transfer JSON is a **delta vs download**: omit any entity row that already exists unchanged, even when FKs still point at it. **New** `Company` / `ObjectType` / `Role` / `RequestStatus` / `Workflow` rows are emitted; recycled ones are not. `workflow.reuse: true` skips generating the shared workflow definition.

## Steps

### 1. Write spec v2

See [`docs/transfer/spec-format.md`](../docs/transfer/spec-format.md).

Use nested `layout.tabs[]` → `sections[]` → `fields[]`. Inbox `onGrid`: [ongrid.md](../docs/entities/ongrid.md) (seven default layouts on a new object). Optional `spec/subgrids.yaml` for a type-5 subgrid — emit `templates[].access` and per-step `workflow.steps[].access` for the parent type-5 line or the widget is hidden; emit `subgrids.<key>.onGrid` or the subgrid **table** has no columns ([add-subgrid.md](add-subgrid.md)). Optional `spec/language-table.yaml` for translated labels ([localization.md](../docs/entities/localization.md)); canonical `name` stays English. Optional `spec/comments.yaml` for Admin HTML comments ([comments.md](../docs/entities/comments.md)). Optional tree `icon` / `color` on `object`, `objectType`, `company` — [spec-format.md](../docs/transfer/spec-format.md#tree-icons-and-colors).

### 2. Allocate IDs

New objects: omit `ids.base` (each table starts at 9000) or set a per-table map (`ObjectLine: 9112` → next field is 9113). After import, run **extract** to fill `ids.explicit`, `ids.byTable`, and site-wide `ids.base` (see [`spec-format.md`](../docs/transfer/spec-format.md#ids-and-round-trip)).

### 3. Emit rows + hierarchy

Generator produces:

| Output | Content |
|--------|---------|
| Table rows | Object, ObjectLineTab, ObjectLineSection, ObjectLine, … |
| `ObjectSetup` edges | Parent→child instance links for Admin tree |
| `ObjectMap` pairs | Schema relationships used |
| `TransferInfo` | `OBJECT` / `1.3.0` |

Follow [`dependency-order.md`](dependency-order.md) for FK logic.

### 4. Layout hierarchy chain

For each field, generator emits:

```
Object → ObjectLine
ObjectLine → ObjectLineTab
ObjectLineTab → ObjectLineSection
ObjectLine → ObjectSub          # type 5; ObjectSub tree is emitted first
```

One section edge per section (not per field). Translations: `Parent → LanguageTable` from `spec/language-table.yaml`. Comments: `Parent → TableComments` from `spec/comments.yaml`. Optional subgrid: [add-subgrid.md](add-subgrid.md).

### 5. onGrid

Canonical: [ongrid.md](../docs/entities/ongrid.md). YAML: [spec-format.md](../docs/transfer/spec-format.md#ongrid).

- `onGrid.fields.<code>` → ObjectLine display flags
- `onGrid.layouts[]` → ObjectLineOnGrid placement. For a **new object**, write **seven** layouts: Items Grid Large/Medium/Small, Items Table Large/Medium/Small, Mobile Items Grid Small. **Grid and Table:** Medium ≈ ½ Large, Small ≈ ½ Medium — fewer columns per letter, extra `T`/`A`/`B` rows. Phone: `row: T` then `A` (not `B`).
- Do not spec Tasks / Relation / Relation Map / Mobile Tasks unless asked.
- System columns (Role, Status, …) use `columns[].systemLine`, not `field`.
- Edge: `Object → ObjectLineOnGrid`
- Subgrid table: `subgrids.<key>.onGrid` → ObjectSubLine flags + ObjectSubLineOnGrid (`field` only) — [add-subgrid.md](add-subgrid.md#ongrid)

### 6. Ask which workflow

**Always ask** before writing `spec/workflow.yaml` (do not silent-default `workflow.mode: minimal`). Skip only if the user already chose in the same request.

1. **New workflow** — new `Workflow` row (minimal Draft → Active → Completed unless they described steps).
2. **Existing workflow** — pick from site `env/` (`catalog.yaml` `workflowIds`, `spec/workflow.yaml` name, `ids.explicit.workflowId`). Each option: **object — workflow name — id**.

**Use existing** = share the same `Workflow` Orig. ID on `ObjectDefault.WorkflowID` (copy that object’s `spec/workflow.yaml` + workflow `ids.explicit`, set `workflow.reuse: true`). Unchanged rows stay out of the JSON. Playbook: [AGENT.md § Ask which workflow](../AGENT.md#ask-which-workflow).

### 7. Workflow + template

**New workflow:** Workflow, WorkflowStep, WorkflowStepAction, ObjectDefault, ObjectDefaultLine.

**Existing workflow (`reuse: true`):** ObjectDefault (`WorkflowID` = shared Orig. ID), ObjectDefaultLine, WorkflowStepAccess for this object’s lines. No Workflow / WorkflowStep / WorkflowStepAction rows.

### 8. Generate

```bash
python scripts/generate-object-transfer.py my-spec.yaml \
  -o output/object-transfer.json
```

### 9. Deploy (partial)

`/publish` uploads the JSON (`isTest: false`) and precompiles.

### 10. Sync IDs after import

If Xeelo assigned new IDs (`Import as New`), re-export the object and extract:

```bash
python scripts/extract-object-transfer-to-spec.py export.xml \
  --merge projects/my-object -o projects/my-object
```

Commit updated `ids.explicit`. Further generates use **Import with Orig. ID**.

## Tables in minimal create_object package

`Company`, `ObjectType`, `Object`, `ObjectLineTab`, `ObjectLineSection`, `ObjectLine`, `ObjectSub?`, `ObjectSubLineTab?`, `ObjectSubLineSection?`, `ObjectSubLine?`, `ObjectSubLineOnGrid?`, `ObjectSubDefault?`, `ObjectSubDefaultLine?`, `ObjectLineLookup?`, `ObjectLineLookupValue?`, `ObjectLineAutoNumber?`, `ObjectLineOnGrid?`, `Role`, `RequestStatus`, `Workflow`, `WorkflowStep`, `WorkflowStepAction`, `ObjectDefault`, `ObjectDefaultLine`

## Validate

- User chose new vs existing workflow (not a silent minimal default)
- JSON object keyed by table name (same shape as DB-transfer download)
- Only tables the spec emits; no TransferInfo / ObjectSetup
- Unique slots; combo has reference; lookup maps live in `spec/lookups.yaml`; autonumbers in `spec/autonumbers.yaml`
- onGrid `field` codes match layout field codes; new object has seven default layouts ([ongrid.md](../docs/entities/ongrid.md#default-for-a-new-object))
