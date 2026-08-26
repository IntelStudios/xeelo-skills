# Recipe: Add Workflow

Extend or replace workflow on an existing object.

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

## Referencing existing roles/statuses

Do **not** recreate `Role` / `RequestStatus` unless building a greenfield site.

Reference by ID in spec:

```yaml
workflow:
  roles:
    requestorId: 1
    ownerId: 2
  statuses:
    draftId: 1
    activeId: 2
    completedId: 3
```

Query target DB if IDs differ:

```sql
SELECT RoleID, RoleName FROM dbo.Role WHERE IsActive = 1;
SELECT RequestStatusID, RequestStatusName FROM dbo.RequestStatus WHERE IsActive = 1;
```

## Sequential named-role approval

A three-step approval is a `workflow.mode: full` chain. Unique index on a step is `(WorkflowID, RoleID, RequestStatusID)` — give each level its **own role and status**. Duplicate button names (`Approve` / `Reject` on every step) need `key` so generate and `languageTable.stepActions` stay unique ([spec-format.md](../docs/transfer/spec-format.md#roles-and-statuses)).

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
      - key: reject_l1
        name: Reject
        role: requestor
        status: draft
        styleId: 2
        order: 20
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
