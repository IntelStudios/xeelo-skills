# Workflow

Process definition for requests on an object.

Schemas: [`Workflow.json`](../data/schemas/Workflow.json), [`WorkflowStep.json`](../data/schemas/WorkflowStep.json), [`WorkflowStepAction.json`](../data/schemas/WorkflowStepAction.json), [`WorkflowStepAccess.json`](../data/schemas/WorkflowStepAccess.json)

## Workflow

**UI:** Workflow

Header for a process. Linked to object via `ObjectDefault.WorkflowID` (not direct FK on Workflow).

| Column | Semantics |
|--------|-----------|
| `WorkflowName` | Process name |
| `RoleID`, `RequestStatusID` | Initial state when request is **created** |
| `NotificationID` | Notification on create |
| `ExportFailRoleID`, `ExportFailRequestStatusID` | State when export fails |
| `RecallRoleID`, `RecallRequestStatusID` | State when request recalled |
| `WorkflowFailRoleID`, `WorkflowFailRequestStatusID` | State on workflow failure |

## WorkflowStep

**UI:** Workflow Step

One step = role + request status (+ optional org chart restriction).

| Column | Semantics |
|--------|-----------|
| `WorkflowStepName` | Step label. **Not unique** — Admin often leaves the default **Added by system**. Unique index is `(WorkflowID, RoleID, RequestStatusID)`. Spec: optional `workflow.steps[].key` when names collide (`added_by_system_3698`); omit `key` when `name` is unique. |
| `RoleID` | Who acts in this step |
| `RequestStatusID` | Status while in this step |
| `UserOrgChartGroupID` | Optional org chart filter |
| `WorkflowStepSuccessMessage` | Message after transition (supports `{RequestID}`, `{RoleName}`, `{RequestStatusName}`) |

Unique index: `(WorkflowID, RoleID, RequestStatusID)`.

## WorkflowStepAccess

**UI:** Object line / Workflow step → Editable / Visible (grouped by request status).

Which object lines are **visible** and **editable** while the request is on a workflow step (e.g. status Open). Site refresh (`spRefreshWorkflowStepAccess`) inserts a row per (step, line) with `IsEditable=0`, `IsVisible=1`. A form button (type 18) stays disabled until its line is editable on that step.

| Column | Semantics | Refresh default |
|--------|-----------|-----------------|
| `WorkflowStepAccessIsEditable` | Line editable in this step | `0` |
| `WorkflowStepAccessIsVisible` | Line visible in this step | `1` |

Spec: `workflow.steps[].access` — see [spec-format.md](../transfer/spec-format.md#full-cars-account). Object Transfer edge: `WorkflowStep → WorkflowStepAccess`. Same dual-list as template **ObjectDefaultAccess** (create) and **ObjectUpdateAccess** (EditableUpdate); refresh defaults differ — [object-model.md](object-model.md#create-form-access-objectdefaultaccess).

## WorkflowStepAction

**UI:** Workflow Step Action — transition buttons.

| Column | Semantics |
|--------|-----------|
| `WorkflowStepActionName` | Button label |
| `WorkflowStepActionOrder` | Display order (use 10, 20, 30…) |
| `RoleID`, `RequestStatusID` | **Target** state after action |
| `WorkflowStepActionStyleID` | Button style — [`data/enums/WorkflowStepActionStyle.json`](../data/enums/WorkflowStepActionStyle.json) |
| `WorkflowStepActionIsCommented` | Comment required |
| `WorkflowStepActionConfirmMethod` | QR / Push / TOTP confirmation |
| `WorkflowStepActionReopenTypeID` | Reopen behaviour after action |

## Role & RequestStatus

**UI:** Role · Request Status

Reference data defined in spec — **always emitted** in transfer with stable IDs from `ids.explicit.roles` / `statuses`. Workflow steps reference role/status **keys**.

## Related: Update actions

**ObjectUpdateAction** (object-level) is **not** a **WorkflowStepAction**. A workflow button named “Update” is still a transition button, not an update action.

Update actions appear on **completed** requests and create a **new request version** (`RequestCode` unchanged). Optional `WorkflowID` on the action sets the workflow for that new version.

See [update-actions.md](update-actions.md).

When creating a **new object** or **update action**, always ask whether to create a new workflow or reuse an existing one (list from site `env/`). See [AGENT.md § Ask which workflow](../../AGENT.md#ask-which-workflow).

## Recipe

[`recipes/add-workflow.md`](../recipes/add-workflow.md) · [`recipes/create-object.md`](../recipes/create-object.md) · [`recipes/add-update-action.md`](../recipes/add-update-action.md)

## DB transfer

`Workflow`, `WorkflowStep`, `WorkflowStepAction`, `Role`, `RequestStatus`, `WorkflowStepActionStyle` — all in transfer scope.
