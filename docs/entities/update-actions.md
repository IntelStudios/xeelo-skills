# Update Actions (ObjectUpdateAction)

User-facing **update actions** create a **new version** of an existing request after the current version is **Completed**. Configuration lives on the **Object**; runtime behaviour is driven by `spRequestInsert` (`RequestTypeID` 2 = Update, 3 = UpdateEmpty).

Schemas: [`ObjectUpdateAction.json`](../data/schemas/ObjectUpdateAction.json), [`ObjectUpdateAccess.json`](../data/schemas/ObjectUpdateAccess.json)

Spec fragment: [`spec/update-actions.yaml`](../transfer/spec-format.md#update-actions-specupdate-actionsyaml)

## Do not confuse

| Entity | Purpose |
|--------|---------|
| **ObjectUpdateAction** | User clicks update → new request version (`RequestCode` unchanged) |
| **WorkflowStepAction** | Workflow transition button (may be named “Update” — different entity) |
| **WorkflowStepObjectAction** | Automated `ObjectAction` on a workflow step (post-submit, via `spObjectActionExecute`) |

## Request versioning

| Column / concept | Meaning |
|------------------|---------|
| `RequestCode` | Shared identity across all versions of one logical request |
| `RequestID` | Primary key — **new row** on each update |
| `RequestTypeID` | `1` Create, `2` Update (copy data), `3` UpdateEmpty (header only) |
| `ObjectUpdateActionID` | Set on update versions — drives access, workflow, reopen |
| `RequestLast` | Tracks `LastRequestID` / `LastCompletedRequestID` per `RequestCode` |

New update always copies from the **latest** version (`fnRequestViewLastRequestCode`).

## Data model

```text
Object (1) ──< ObjectUpdateAction (N)
                    │
                    ├── FK ObjectDefaultID?  → template scope (NULL = all templates)
                    ├── FK WorkflowID?       → workflow for new version (NULL = template workflow)
                    ├── FK ObjectLineTabFocusLeftID/RightID
                    │
                    ├──< ObjectUpdateAccess (line/subline editable + visible flags)
                    ├──< ObjectUpdateActionCondition (grid visibility rules)
                    └──< ObjectUpdateMessage (object messages on update form)

ObjectUpdateActionUserList  → per-user allow (User admin; not in transfer)
```

Object Transfer edges: [`data/object-transfer-map.json`](../data/object-transfer-map.json) — `Object → ObjectUpdateAction → {Access, Condition, Message}`.

## ObjectUpdateAction (header)

**UI:** Object Detail → Update Actions

| Column | Semantics |
|--------|-----------|
| `ObjectUpdateActionName` | Display name (i18n) |
| `ObjectUpdateActionOrder` | Sort order (use 10, 20, 30…) |
| `ObjectDefaultID` | Limit to one template; NULL = all templates |
| `WorkflowID` | Workflow for the **new version** after update |
| `ObjectUpdateActionIsQuick` | Process immediately without save step |
| `ObjectUpdateActionReopenTypeID` | Reopen behaviour after save |
| `ObjectLineTabFocusLeftID/RightID` | Tab focus in update form |
| `IsActive` | Soft disable |

Admin hints: [`data/table-hints.json`](../data/table-hints.json) (`ObjectUpdateAction*`)

## ObjectUpdateAccess

Per-line (and optional subgrid column) flags during **EditableUpdate** mode. Same Admin Visible / Editable dual-list as **template create access** (`ObjectDefaultAccess`) and **workflow step access**.

| Column | Refresh insert | Semantics |
|--------|----------------|-----------|
| `ObjectLineIsEditableUpdate` | 0 | Field editable during update |
| `ObjectLineIsVisibleUpdate` | 1 | Field visible during update |

Site refresh inserts a row per (action, line) as **visible, not editable**. Spec `updateActions[].access` must list fields that should be editable (or hidden). `editable: true` forces `visible: true`.

Applied via `ProcessEditableUpdateAccess` when the new version is unsaved (`RequestTypeID` 2/3). **ObjectAction** (server automation) has no line-access table.

This is not `templates.fields.hidden` / `alwaysDisabled` — see [object-model.md](object-model.md#create-form-access-objectdefaultaccess).

## ObjectUpdateActionCondition

Controls **which update actions appear** on a completed request (`spRequestUpdateActionList`). Evaluates field values with OR semantics per line (one passing condition on a line clears failures for that line).

Condition types (seed): None, Contains, Equals, Between, Is empty, … — see `ObjectUpdateActionConditionType`.

## ObjectUpdateMessage

Links `ObjectMessage` rows to an update action with visibility flag.

## Runtime flow

1. Request reaches **Completed** (`CompletedDate` set).
2. `spRequestUpdateActionList` returns eligible `ObjectUpdateActionID`s (conditions).
3. C# filters by `ObjectUpdateActionUserList` / user cache.
4. User selects action → `POST /api/Request/{objectId}/{requestId}/Update?updateActionId=`.
5. `spRequestInsert` `@RequestTypeID = 2`:
   - Resolves latest version by `RequestCode`
   - Sets `WorkflowID` from action, else template
   - Inserts new `Request` with same `RequestCode`, copies `RequestData*`
6. UI opens in **EditableUpdate**; previous values shown for diff.

GraphQL: `createType: UPDATE | UPDATE_EMPTY`, `updateAction: Int`.

## Admin setup

| Step | Location |
|------|----------|
| Define actions | Object Detail → **Update Actions** |
| Conditions | Action → Conditions |
| Line access | Action → Access (editable/visible tree) |
| User allow list | Action → Access → Users **or** User → Access Detail → Update Action |
| Messages | Action → Access → Messages |

## Workflow linkage

- **`ObjectUpdateAction.WorkflowID`** — workflow assigned to the **new request version** (not the completed version’s current step).
- **`RefreshWorkflowToObjectView`** unions workflows from `ObjectDefault` and `ObjectUpdateAction`.
- Template workflow (`ObjectDefault.WorkflowID`) is fallback when action has no workflow.

## Planned: M:N with WorkflowStepAction

**Target (not in current platform schema):** junction table (e.g. `WorkflowStepActionObjectUpdateAction`) linking which **ObjectUpdateAction** rows are offered from which **WorkflowStepAction** buttons.

**Current behaviour:** update actions appear on any **Completed** request for the object (subject to conditions + user list), independent of which workflow step action completed the request.

Document both models in recipes and specs until junction table ships.

## Transfer scope

| In Object/DB transfer | Not in transfer |
|-----------------------|-----------------|
| `ObjectUpdateAction`, `ObjectUpdateAccess`, `ObjectUpdateActionCondition`, `ObjectUpdateMessage` | `User`, `ObjectUpdateActionUserList` |

## Spec / tooling

- Fragment: `spec/update-actions.yaml` — see [spec-format.md](../transfer/spec-format.md)
- Extract/generate: `scripts/ot_builder/extract.py`, `rows.py`
- Golden sample: [`projects/cars/`](../projects/cars/) (action id 5118 in OT)

## Recipe

[`recipes/add-update-action.md`](../recipes/add-update-action.md)
