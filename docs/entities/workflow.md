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
| `WorkflowStepIsSuppressSave` | Admin **Suppress save**. Spec: `steps[].suppressSave`. Hides the **footer Save** on that step (`showSaveBtn`). Form **Button** lines (type 18) still save on click. |
| `IsActive` | Soft-disable. Spec: `steps[].isActive: false`. Object Transfer does not delete the step. |

Unique index: `(WorkflowID, RoleID, RequestStatusID)`.

`spRefreshWorkflowStep` (after Workflow / WorkflowStepAction changes) keeps a step **active** only when its `(RoleID, RequestStatusID)` is the workflow **header** state, an export-fail / workflow-fail / recall target, or the **target** of an active `WorkflowStepAction` on an active step. A step that exists only in spec — including one reached solely by ObjectAction **Change role and status** — is stored with `IsActive = 0`. Object Transfer `IsActive: 1` does not win against that refresh. Add a `WorkflowStepAction` targeting the extra status (footer transition button) even if the form also has a type-18 button.

## WorkflowStepAccess

**UI:** Object line / Workflow step → Editable / Visible (grouped by request status).

Which object lines are **visible** and **editable** while the request is on a workflow step (e.g. status Open). Site refresh (`spRefreshWorkflowStepAccess`) inserts a row per (step, line) with `IsEditable=0`, `IsVisible=1`. A form button (type 18) stays disabled until its line is editable on that step.

| Column | Semantics | Refresh default |
|--------|-----------|-----------------|
| `WorkflowStepAccessIsEditable` | Line editable in this step | `0` |
| `WorkflowStepAccessIsVisible` | Line visible in this step | `1` |

Spec: `workflow.steps[].access` — see [spec-format.md](../transfer/spec-format.md#full). Object Transfer edge: `WorkflowStep → WorkflowStepAccess`. Same dual-list as template **ObjectDefaultAccess** (create) and **ObjectUpdateAccess** (EditableUpdate); refresh defaults differ — [object-model.md](object-model.md#create-form-access-objectdefaultaccess).

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
| `WorkflowStepActionReopenTypeID` | Reopen after this **workflow button**. Spec: `workflow.steps[].actions[].reopenOnSave`. Same catalog as template — [`ReopenActionType.json`](../data/enums/ReopenActionType.json). Omit/`none` = close. |
| `IsActive` | Soft-disable the footer button. Spec: `steps[].actions[].isActive: false`. Omit the action from spec and the site row stays active. |

## Role & RequestStatus

**UI:** Role · Request Status

Reference data defined in spec. Emitted in Object Transfer only when the row is **new or changed** vs the latest download — same delta rule as every other table. Recycled workflow (`workflow.reuse: true`) skips generating the shared process; bind `ObjectDefault.WorkflowID` to the existing Orig. ID. Workflow steps in spec still reference role/status **keys**.

## Soft-delete (`IsActive`)

Object Transfer **upserts** by Orig. ID; it does not delete site rows. To hide an entity, emit the same Orig. ID with **`isActive: false`** (`IsActive = 0`). Omitting it from spec leaves the live row unchanged.

Applies to `ObjectUpdateAction`, `ObjectAction`, `Role`, `RequestStatus`, `WorkflowStep`, `WorkflowStepAction`, and other transferred tables with `IsActive`. Extract lists **active** update/object actions only — keep `isActive: false` in the change-loop spec so a later generate cannot turn the row back on. Extract **does** write `isActive: false` on inactive workflow steps and step actions so a later generate keeps them off.

## Related: Update actions

**ObjectUpdateAction** (object-level) is **not** a **WorkflowStepAction**. A workflow button named “Update” is still a transition button, not an update action.

Update actions appear on **completed** requests and create a **new request version** (`RequestCode` unchanged). Optional `WorkflowID` on the action sets the workflow for that new version.

See [update-actions.md](update-actions.md).

When creating a **new object** or **update action**, always ask whether to create a new workflow or reuse an existing one (list from site `env/`). See [AGENT.md § Ask which workflow](../../AGENT.md#ask-which-workflow).

## Recipe

[`recipes/add-workflow.md`](../recipes/add-workflow.md) · [`recipes/create-object.md`](../recipes/create-object.md) · [`recipes/add-update-action.md`](../recipes/add-update-action.md)

## DB transfer

`Workflow`, `WorkflowStep`, `WorkflowStepAction`, `Role`, `RequestStatus`, `WorkflowStepActionStyle` — all in transfer scope.
