# Object Actions (ObjectAction)

Server-side automations on an **Object**, executed during request refresh after save/workflow events (`spObjectActionExecute`). Configuration lives on the object and is wired to workflow steps via `WorkflowStepObjectAction`.

Schemas: [`ObjectAction.json`](../data/schemas/ObjectAction.json), [`ObjectActionParam.json`](../data/schemas/ObjectActionParam.json), [`ObjectActionCondition.json`](../data/schemas/ObjectActionCondition.json), [`WorkflowStepObjectAction.json`](../data/schemas/WorkflowStepObjectAction.json)

Spec fragment: [`spec/object-actions.yaml`](../transfer/spec-format.md#object-actions-specobject-actionsyaml)

## Do not confuse

| Entity | Purpose |
|--------|---------|
| **ObjectAction** | Automated server action on Save / Workflow (`spObjectActionExecute`) |
| **ObjectUpdateAction** | User clicks update on a **Completed** request → new request version |
| **WorkflowStepAction** | Workflow transition button |
| **ObjectLine type 18 (Button)** | Form control; click sets value `1` and **saves**, which then runs ObjectActions |

A form button does **not** reference `ObjectActionID`. Typical pattern: Button line → Save → `WorkflowStepObjectAction` → `ObjectAction` (optionally conditioned on the button value). The button line must also be **editable** on the current workflow step (`WorkflowStepAccess`).

For **Run Node.js (Last)** that talks to GraphQL: button condition → Last action → `Select_` / `Mutate_` in `CustomJS` → optional result memo. Self-update of **this** request must not refresh; `CREATE` on another object may. See [nodejs-graphql-patterns.md](../../recipes/nodejs-graphql-patterns.md) and [graphql.md](graphql.md).

## Runtime

```text
Save / SaveNew / WorkflowAction / …
  → spRequestRefreshGeneral
      → spObjectActionExecute (IsLast=0)
      → calculations / exports / …
      → spObjectActionExecute (IsLast=1)   # e.g. Run Node.js (Last)
```

Actions are resolved from the current request’s workflow step (`WorkflowStepObjectAction`), then filtered by `ObjectActionCondition` (`fnRequestLineDataCondition`).

**Last** types have `ObjectActionType.ObjectActionTypeIsLast = 1` (UI suffix “(Last)”). They run in the second execute pass.

## Data model

```text
Object (1) ──< ObjectAction (N)
                  │
                  ├── ObjectActionTypeCode → ObjectActionType (system catalog, not transferred)
                  ├──< ObjectActionParam (type param code + value)
                  └──< ObjectActionCondition (line + condition type)

WorkflowStep (1) ──< WorkflowStepObjectAction (N) ──> ObjectAction
```

Object Transfer edges: [`data/object-transfer-map.json`](../data/object-transfer-map.json) — `Object → ObjectAction → {Param, Condition}`; `WorkflowStep → WorkflowStepObjectAction`.

**Not transferred:** `ObjectActionType`, `ObjectActionTypeParam`, `ObjectActionConditionType` (site seed tables).

## ObjectAction (header)

**UI:** Object Detail → Object Actions

| Column | Semantics |
|--------|-----------|
| `ObjectActionName` | Display name |
| `ObjectActionTypeCode` | Type from `ObjectActionType` (e.g. `spEndPointRunNodeJSMainLast`) |
| `ObjectActionOrder` | Sort / run order (10, 20, 30…) |
| `IsActive` | Soft disable |

## Run Node.js (Last)

Type code **`spEndPointRunNodeJSMainLast`**. Executable calls `spEndPointRunNodeJSMain`.

**Always ESM** for new actions. Scripts, full `Context`, and the no-refresh rule: [nodejs-esm.md](nodejs-esm.md). Schema names, query/mutation variants, `lines` vs `linesFormatted`: [graphql.md](graphql.md).

| Param | Default | Meaning |
|-------|---------|---------|
| `CustomJS` | `export async function main()` | ESM script; return value becomes the HTTP response body |
| `EndPointRunESM` | `"1"` | `POST /execute-esm` |
| `EndPointRunWait` | `"1"` | Wait and write response onto object lines. `"0"` = do not wait (async); timeout still applies to the ESM process |
| `EndPointRunTimeout` | `"60000"` | Timeout ms. Raise for bulk GraphQL CREATE (import); see [nodejs-graphql-patterns.md](../../recipes/nodejs-graphql-patterns.md#6-batch--parallel-create) |
| `ResponseCodeObjectLineID` | — | Line for HTTP status (types 1, 2, 3, 4, 11, 12) |
| `ResponseTextObjectLineID` | — | Line for response body — use **Memo (11)** for long text |
| `ApplicableEventType` | `"Save,SaveNew"` | Comma list: `SaveNew,Save,WorkflowAction,…` |

With `EndPointRunWait=1`, `spRequestUpdate` writes `EndPointRunResponseText` to `ResponseTextObjectLineID`.

**When mutating the current request from an ObjectAction, do not trigger refresh in the mutation** (`withRefresh: false`, omit `createType`). Nested `spRequestRefresh` re-runs this action and loops. Periodic JS is the opposite: GraphQL mutate **must** refresh ([nodejs-esm.md](nodejs-esm.md#periodic--graphql-mutate-must-refresh)).

To re-run Last on **another completed** request, `withRefresh` on that id is not an update action — use `createType: UPDATE` + that object’s `updateAction` ([nodejs-graphql-patterns.md](../../recipes/nodejs-graphql-patterns.md#8-start-update-action-on-completed-requests)).

## ObjectActionCondition

Same type catalog as update-action conditions (Contains, Equals text/number, Is empty, …). Spec slugs: `equals_text`, `is_empty`, …

Gate a button-triggered action with `equals_text` / param `1` on the button field.

## Change role and status (Last)

Three seed types. All are **Last**. They change `Request.RoleID` / `RequestStatusID` on the **same** request (no new version — not `ObjectUpdateAction`). Target role+status must exist as an **active** `WorkflowStep` on the request’s workflow, or the SP returns DANGER.

| `typeCode` | Admin name | Behaviour |
|------------|------------|-----------|
| `spRequestWorkflowUpdate` | Change role and status of request (Last) | This `RequestID` only. Clears `RequestUserExclusion`. Sets/clears Completed and Canceled from the **target** status. |
| `spRequestWorkflowUpdateAllVersion` | Change role and status of request (all versions) (Last) | Same update on **every submitted** version with the same `RequestCode`. |
| `spRequestWorkflowUpdateExclusion` | Change role and status of request keep exclusion (Last) | Like the first, but keeps `RequestUserExclusion`. |

Typical in-progress edit: form buttons + first type (not all-versions). Params `RoleID1` / `RequestStatusID1` — spec `{ role: requestor }` / `{ status: updating }` (or raw IDs). Condition the action on the button; assign it only to the **source** step. Hide footer Save with `steps[].suppressSave` so users transition via those buttons, not `WorkflowStepAction`.

Do **not** confuse with **WorkflowStepAction** (workflow transition buttons in the request footer).

## WorkflowStepObjectAction

Assigns an `ObjectAction` to a `WorkflowStep` (optional `RequestTypeID`). Without this link the action never runs.

## Spec / tooling

- Fragment: `spec/object-actions.yaml` — see [spec-format.md](../transfer/spec-format.md)
- Scripts / Context: [nodejs-esm.md](nodejs-esm.md)
- GraphQL schema: [graphql.md](graphql.md)
- Generate/extract: `scripts/ot_builder/object_actions.py`, `rows.py`, `extract.py`
- Recipes: [`add-object-action.md`](../../recipes/add-object-action.md), [`nodejs-graphql-patterns.md`](../../recipes/nodejs-graphql-patterns.md)
