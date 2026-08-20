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

## Optional: WorkflowStepAccess

Controls which object lines are visible/editable per step. Site refresh creates a row for every line with **visible yes, editable no**. Add `access` on a full-mode step when a field must be editable after create (typical: a form button on status Open):

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

Create-form and update-form use the same `{field, editable, visible}` list on `templates[].access` (**ObjectDefaultAccess**, refresh: both yes) and `updateActions[].access` (**ObjectUpdateAccess**, refresh: visible yes, editable no). See [object-model.md](../docs/entities/object-model.md#create-form-access-objectdefaultaccess).

## Hints

See [`data/table-hints.json`](../data/table-hints.json) entries for `Workflow`, `WorkflowStep`, `WorkflowStepAction`.
