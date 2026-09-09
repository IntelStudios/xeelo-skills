# Recipe: Add Workflow

Extend or replace workflow on an existing object.

## Ask which roles and statuses (new workflow)

When creating a **new** workflow (not `workflow.reuse: true`), **always ask both** before writing `roles:` / `statuses:` / `ids.explicit`. Do not silent-default. Skip a side only if the user already chose it in the same request. The two choices are **independent**. Playbook: [AGENT.md § Ask which workflow](../AGENT.md#ask-which-workflow).

**Roles** — list from `env/shared/roles.yaml`: **name — id** (optional `isRequestor` / `isOwner`). Empty or stale env → `/download-db` first, or only “new roles”.

1. **Existing roles** (Recommended) — bind `ids.explicit.roles`. Copy `roles:` **verbatim** from that file (`name`, flags, `isActive`). **Do not** rename or flip `isRequestor` / `isOwner`. Generate omits existing `Role` Orig. IDs even if spec cells differ. Omit `languageTable.roles` and comments for those keys.
2. **New roles** — define **new** `roles:` keys only. `UserAccess` is not in Object Transfer — assign users on the object in Admin after publish ([users-and-access.md](../docs/entities/users-and-access.md)).

**Statuses** — list from `env/shared/statuses.yaml`: **name — id** (optional `order`, `isCompleted`, `isCanceled`). Empty or stale env → `/download-db` first, or only “new statuses”.

1. **Existing statuses** (Recommended) — bind `ids.explicit.statuses`. Copy `statuses:` **verbatim** from that file (`name`, `order`, `isCompleted`, `isCanceled`, `isActive`). **Do not** rename, flip completed/canceled, or change `order`. Generate omits existing `RequestStatus` Orig. IDs even if spec cells differ. Omit `languageTable.statuses` and comments for those keys.
2. **New statuses** — define **new** `statuses:` keys only.

Reuse of an existing workflow skips both — roles and statuses come with the shared process.

## Minimal workflow (default)

Generated automatically by `workflow.mode: minimal` in spec:

```
[Draft / Requestor] --Submit--> [Active / Owner] --Complete--> [Completed / Requestor]
```

## Tables

| Table | Purpose |
|-------|---------|
| `Workflow` | Header: name, initial role/status, fail/recall handlers |
| `WorkflowStep` | One row per role+status combination in the flow |
| `WorkflowStepAction` | Transitions between steps |
| `ObjectDefault` | Must reference `WorkflowID` |

## Workflow columns (key)

From [`data/schemas/Workflow.json`](../data/schemas/Workflow.json):

- `WorkflowName`
- `RoleID`, `RequestStatusID` — state when request is **created**
- `ExportFailRoleID`, `ExportFailRequestStatusID` — optional error handling
- `RecallRoleID`, `RecallRequestStatusID` — optional recall handling

## WorkflowStepAction columns (key)

- `WorkflowStepActionName` — button label
- `WorkflowStepActionOrder` — sort order (use 10, 20, 30…)
- `RoleID`, `RequestStatusID` — **target** state after action
- `WorkflowStepActionStyleID` — 1 = Positive green (see [`data/enums/WorkflowStepActionStyle.json`](../data/enums/WorkflowStepActionStyle.json))
- `WorkflowStepActionReopenTypeID` — Admin **Reopen on Action**. Spec: `actions[].reopenOnSave`. **New actions: `open-only-assigned`** unless the user asks otherwise. Omit/`none`/`close` = request closes after the button.

## Referencing existing roles/statuses

After the user picks **existing** catalog rows, copy the site definition **verbatim** and bind Orig. IDs. Do **not** emit an upsert that would change `RoleName` / `RequestStatusName`, requestor/owner flags, completed/canceled flags, `order`, or `isActive`:

```yaml
# Copy from env/shared/roles.yaml + statuses.yaml (flags as on the site — not defaults)
roles:
  requestor:
    name: Requestor
    isRequestor: true
    isOwner: false
  owner:
    name: Owner
    isRequestor: false
    isOwner: true
statuses:
  draft:
    name: Draft
    order: 10
    isCompleted: false
    isCanceled: false
```

`ids.explicit.roles` / `statuses` must be the live Orig. IDs from those shared files. Generate omits those `Role` / `RequestStatus` rows vs download even if a spec cell would differ. Query the site only if env is empty:

```sql
SELECT RoleID, RoleName FROM dbo.Role WHERE IsActive = 1;
SELECT RequestStatusID, RequestStatusName FROM dbo.RequestStatus WHERE IsActive = 1;
```

## Sequential named-role approval

A three-step approval is a `workflow.mode: full` chain. Unique index on a step is `(WorkflowID, RoleID, RequestStatusID)` — give each level its **own role and status**. If those roles or statuses are not on the site, that is the **new roles** / **new statuses** path from the ask above. Duplicate button names (`Approve` / `Reject` on every step) need `key` so generate and `languageTable.stepActions` stay unique ([spec-format.md](../docs/transfer/spec-format.md#roles-and-statuses)).

```
[Draft / Requestor] --Submit--> [Pending L1 / Team lead]
  --Approve--> [Pending L2 / Department head]
  --Approve--> [Pending L3 / Director]
  --Approve--> [Completed / Requestor]
Reject on each approval step returns to Draft / Requestor (styleId 2).
```

```yaml
workflow:
  mode: full
  steps:
  - name: Draft
    role: requestor
    status: draft
    actions:
      - name: Submit
        role: team_lead
        status: pending_team_lead
        styleId: 1
        order: 10
        reopenOnSave: open-only-assigned
  - name: Team lead
    role: team_lead
    status: pending_team_lead
    actions:
      - key: approve_l1
        name: Approve
        role: department_head
        status: pending_department
        styleId: 1
        order: 10
        reopenOnSave: open-only-assigned
      - key: reject_l1
        name: Reject
        role: requestor
        status: draft
        styleId: 2
        order: 20
        reopenOnSave: open-only-assigned
```

Rename an existing footer button (e.g. Complete → Submit) by **keeping** its `ids.explicit.workflowStepActions` Orig. ID. Object Transfer does not delete leftover `WorkflowStepAction` rows.

`UserAccess` is not in Object Transfer — assign the new roles on the object in Admin after publish ([users-and-access.md](../docs/entities/users-and-access.md)).

## Optional: WorkflowStepAccess

Controls which object lines are visible/editable per step. Site refresh creates a row for every line with **visible yes, editable no**, but **Object Transfer does not run that refresh**. For a **new** line, emit `access` on every step that should show it. A missing row hides the field (including a type-5 subgrid). After extract, add `access` on a full-mode step when a field must be editable after create (typical: a form button on status Open):

```yaml
workflow:
  mode: full
  steps:
    - name: Draft
      role: requestor
      status: open
      actions: []
      access:
        - field: LOAD_TX
          editable: true
```

Reuse the site `WorkflowStepAccessID` in `ids.explicit.workflowStepAccess` (`Draft/LOAD_TX`) after the first DB extract.

Create-form and update-form use the same `{field, editable, visible}` list on `templates[].access` (**ObjectDefaultAccess**, refresh: both yes — **emit it for a new line**) and `updateActions[].access` (**ObjectUpdateAccess**, refresh: visible yes, editable no). See [object-model.md](../docs/entities/object-model.md#create-form-access-objectdefaultaccess).

## Hints

See [`data/table-hints.json`](../data/table-hints.json) entries for `Workflow`, `WorkflowStep`, `WorkflowStepAction`.
