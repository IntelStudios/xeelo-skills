# Add Object Action

Add an **ObjectAction** so the server runs automation after **Save** or a workflow event (via `spObjectActionExecute`).

Entity reference: [docs/entities/object-actions.md](../docs/entities/object-actions.md). Scripts / `Context`: [docs/entities/nodejs-esm.md](../docs/entities/nodejs-esm.md). GraphQL: [docs/entities/graphql.md](../docs/entities/graphql.md). CustomJS patterns: [nodejs-graphql-patterns.md](nodejs-graphql-patterns.md).

**Defaults for Run Node.js:** `typeCode: spEndPointRunNodeJSMainLast`, `EndPointRunESM: "1"`, `EndPointRunWait: "1"`, `export async function main()`. When the script mutates **this** request, omit `createType` and set `withRefresh: false`.

## Preconditions

- Object exists with layout, **ObjectDefault** template, and a workflow step that stays on the request when the action should run
- For a form **Button**: `ObjectLineTypeID = 18`; `saveAction: 0` (Save — stay on the request). Click saves (`value = 1`), then ObjectActions run. `saveAction: 1` is Save & close.
- Target site already has `ObjectActionType` seed (including `spEndPointRunNodeJSMainLast`)

## Admin UI path

Object Detail → **Object Actions**:

1. Create action — name, type (e.g. **Run Node.js (Last)**), order
2. **Parameters** — Custom JS, wait, response object lines, applicable event types
3. **Conditions** — optional field gates (button `= 1`, combo bind, …)
4. Workflow → Step → **Object Actions** — assign the action to the step

## Spec / Object Transfer path

Optional fragment `spec/object-actions.yaml` (see [spec-format.md](../docs/transfer/spec-format.md)):

```yaml
objectActions:
  - key: load-transactions
    name: Load transactions
    typeCode: spEndPointRunNodeJSMainLast
    order: 10
    workflowSteps: [Draft]
    params:
      CustomJS: |
        import { XeeloGraphQLClient } from "@xeelo/graphql-client";
        export async function main() { return "OK"; }
      EndPointRunWait: "1"
      EndPointRunESM: "1"
      ApplicableEventType: "Save,SaveNew"
      ResponseTextObjectLineID: { field: RESULT_MEMO }
    conditions:
      - field: LOAD_TX
        type: equals_text
        param1: "1"
```

Include in `xeelo-spec.yaml`:

```yaml
includes:
  - spec/object.yaml
  - spec/workflow.yaml
  - spec/object-actions.yaml
  - spec/ids.yaml
```

Generate:

```bash
python scripts/generate-change-loop.py projects/<project>/changes/<slug>
```

**Transfer scope:** `ObjectAction`, `ObjectActionParam`, `ObjectActionCondition`, `WorkflowStepObjectAction`. **Not** `ObjectActionType` (system catalog).

## Checklist

- [ ] Action type code matches site catalog (`spEndPointRunNodeJSMainLast` for Run Node.js Last)
- [ ] ESM defaults: `EndPointRunESM: "1"`, `export async function main()`
- [ ] `workflowSteps` names match `workflow.steps[].name`
- [ ] Button (if used) is type `button`; condition equals `1`
- [ ] Change role and status: `spRequestWorkflowUpdate` (this request) unless you need all versions or keep exclusion; params `{ role }` / `{ status }`; not a `WorkflowStepAction`
- [ ] `ResponseTextObjectLineID` points at a memo/text/number line
- [ ] `EndPointRunWait: "1"` if the result must land on the request
- [ ] Bulk CREATE: batch `input` + limited parallel `client.request`; raise `EndPointRunTimeout` ([nodejs-graphql-patterns.md](nodejs-graphql-patterns.md#6-batch--parallel-create))
- [ ] GraphQL identifiers in `CustomJS` match **env** `object.code` / `fields[].code` after `/download-db` ([graphql.md](../docs/entities/graphql.md))
- [ ] Self-update: no `createType`, `withRefresh: false`; `CREATE` only on a **different** object
- [ ] Completed other requests that need Last: `createType: UPDATE` + `updateAction`, no `lines` ([nodejs-graphql-patterns.md](nodejs-graphql-patterns.md#8-start-update-action-on-completed-requests))
- [ ] Select uses `lines` (valueData), not `linesFormatted`, for calculations
- [ ] Date picker values are `dd-MM-yyyy`; parse by splitting, not `new Date()` — [graphql.md](../docs/entities/graphql.md#date-picker-type-8)
- [ ] Service account **0** has **WRITE** on every object the script mutates ([users-and-access.md](../docs/entities/users-and-access.md))
- [ ] `ids.explicit` populated for Orig. ID import
- [ ] Request stays **editable** on that workflow step (not immediately Completed)
- [ ] Button line is **WorkflowStepAccess editable** on that step (refresh default is not editable → button stays disabled)
- [ ] If the action must not re-run on later Save, clear the button in the same self-update

## Troubleshooting

| Symptom | Check |
|---------|--------|
| Action never runs | Missing `WorkflowStepObjectAction`; wrong step; `ApplicableEventType` filter |
| Runs on every save | Missing condition on the button (or other gate) |
| Result not on the form | `EndPointRunWait` is 0; wrong `ResponseTextObjectLineID`; line type not 1/2/3/4/11/12 |
| Button does nothing | Request already Completed; button hidden by extended validation; button not editable on the workflow step (`WorkflowStepAccess`); extra step `IsActive = 0` because refresh did not see a `WorkflowStepAction` targeting that status |
| Action loops / times out | GraphQL mutation on the **current** request used `withRefresh: true` or `createType` — omit both; see [nodejs-esm.md](../docs/entities/nodejs-esm.md#mutating-the-current-request--no-refresh) |
| Last on other completed requests does not run | `{ requestId, withRefresh: true }` is not an update action — use `createType: UPDATE` + that object’s `updateAction`; see [nodejs-graphql-patterns.md](nodejs-graphql-patterns.md#8-start-update-action-on-completed-requests) |
| CREATE / mutate fails with access | Service account **0** missing WRITE on that object |
| Wrong field / unknown type | `CustomJS` used spec codes that the site overwrote — copy from env; [graphql.md](../docs/entities/graphql.md) |

## Patterns

[nodejs-graphql-patterns.md](nodejs-graphql-patterns.md) — self-update, CREATE another object, Select → compute, combined import-style action.
