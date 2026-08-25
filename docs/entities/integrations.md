# Integrations

Data import/export, automation, and external connectivity.

Labels: [`data/entity-labels.json`](../data/entity-labels.json) · Hints: [`data/table-hints.json`](../data/table-hints.json)

## Export

**Tables:** `Export`, `ExportLine`, `ExportCondition`, `ExportCalculation`

Defines data export from requests (CSV, XML, SQL, Excel).

Key fields (from hints):

- `ExportName` — export definition name
- `ExportTypeID` — CSV/XML/SQL/Excel format
- `ExportDeliveryID` — Download or Email
- `ExportLineTypeID` — object line, fixed value, request metadata, etc.

Often triggered from workflow steps via `WorkflowStepExport`.

## Import

**Tables:** `Import`, `ImportSection`, `ImportSectionLine`

Inbound data pipelines into objects.

## Periodic

**Tables:** `Periodic`, `PeriodicAction`, `PeriodicActionParam`, `PeriodicCondition`, `PeriodicActionCondition`, `PeriodicCalculation`

Scheduled **batch** on one object: pick last-version requests, filter, run ordered actions. **CRON is not on `Periodic`.** Timing is a **Scheduler** line of type `spPeriodicExecute` with param `PeriodicID`. Spec: [`spec/periodics.yaml`](../transfer/spec-format.md#periodics-specperiodicsyaml). Recipe: [`recipes/add-periodic.md`](../../recipes/add-periodic.md).

### Do not confuse

| Entity | Role |
|--------|------|
| **Periodic** | What to run (object, request scope, conditions, actions) |
| **Scheduler** | When to run (Quartz CRON → `spPeriodicExecute`) |
| **ObjectAction** | Save/workflow automation on **one** request (`EventType` Save / SaveNew / …) |
| **ObjectUpdateAction** | User (or GraphQL `createType: UPDATE`) starts a **new request version** |

### Runtime

```text
Scheduler.SchedulerCRON  (Quartz, 7 fields, Europe/Prague)
  → spSchedulerExecute
      → SchedulerLine type spPeriodicExecute {PeriodicID}
          → spPeriodicExecute
              → last-version requests of Periodic.ObjectID
              → filter PeriodicRequestTypeID + PeriodicCondition
              → PeriodicCalculation (type periodic)
              → spPeriodicAction (ordered PeriodicAction)
```

`spPeriodicExecute` builds the list from `fnRequestViewLastObject` (one row per request **code**, latest version). Inactive Periodic is a no-op.

| `PeriodicRequestTypeID` | Spec `requestType` | Scope |
|-------------------------|--------------------|--------|
| `0` | `all` | All last versions |
| `10` | `in_progress` | Last version ≠ last completed |
| `20` | `completed` | Last version = last completed |

Condition type IDs match update-action / object-action conditions (`13` = `equals_text`). Same OR-per-line pattern as elsewhere.

Each **PeriodicAction** re-filters with `PeriodicActionCondition`. Executable comes from `PeriodicActionType` (site seed, not transferred). If the template contains `{RequestID}`, SQL runs **once per remaining request**. `{RequestList}` = one batch call. Otherwise one-shot with no request context.

Manual run: Admin Periodic **Refresh**, or GraphQL `Execute_Periodic(periodicId)` (WRITE on the object). Same SP as the scheduler.

### Node.js action

Type code **`spEndPointRunNodeJSMain`** (not `…Last`). Same Node pipeline as ObjectAction: `EventType = Periodic`, `ScopeID = PeriodicAction_{id}`, GraphQL token = service account **0**. Params: `CustomJS`, `EndPointRunWait`, `EndPointRunTimeout`, `ResponseCodeObjectLineID`, `ResponseTextObjectLineID`, `EndPointRunESM`.

New scripts in this KB are ESM (`EndPointRunESM: "1"`, `export async function main()`). See [nodejs-esm.md](nodejs-esm.md).

**GraphQL mutate from Periodic must refresh.** Periodic is **not** inside `spRequestRefreshGeneral`. Simple `Mutate_` of lines needs `withRefresh: true`; `CREATE` / `UPDATE` / `UPDATE_EMPTY` already refresh. ObjectAction on the **current** request is the opposite (`withRefresh: false`, no `createType`) — [nodejs-esm.md](nodejs-esm.md#periodic--graphql-mutate-must-refresh).

**Per-request cost:** a Node.js periodic on an object with 500 matching entities queues **500** Node runs each tick. Bind the Periodic to the object whose requests you want to process (e.g. **Account** for FIO import), and use conditions to shrink the list. Do not hang a “import payments” periodic on the payment object.

Starting an update action from periodic JS: `createType: "UPDATE"` + `updateAction` on **`Context.RequestID`** (that request is the completed entity in the batch). Pattern: [nodejs-graphql-patterns.md](../../recipes/nodejs-graphql-patterns.md#8-start-update-action-on-completed-requests). Native type `spPeriodicHelpRequestUpdate` can start an `ObjectUpdateAction` without JS.

### Transfer

Email on a batch: PeriodicAction types `spNotificationDataInsert` (single) and `spNotificationDataInsertSummary` (summary). Spec: `params.NotificationID1` / `NotificationID2: { notification: key }`. [notifications.md](notifications.md).

Object Transfer edges: [`data/object-transfer-map.json`](../data/object-transfer-map.json) — `Object → Periodic → {Action, Condition, Calculation}`; `PeriodicAction → {Param, Condition, Notification}`. **Not transferred:** `PeriodicActionType`, `PeriodicConditionType`, `PeriodicRequestType` (site seed). Enum: [`data/enums/PeriodicRequestType.json`](../data/enums/PeriodicRequestType.json).

Schemas: [`data/schemas/Periodic.json`](../data/schemas/Periodic.json) and siblings.

## Scheduler

**Tables:** `Scheduler`, `SchedulerLine`, `SchedulerLineParam`

Site-wide Quartz jobs. Periodics use line type **`spPeriodicExecute`** with param code **`PeriodicID`**. Other line types exist (seed `SchedulerLineType`); this KB generates only the periodic link.

| Column | Meaning |
|--------|---------|
| `SchedulerName` | Display name (i18n) |
| `SchedulerCRON` | Quartz **7-field** expression (`seconds minutes hours day-of-month month day-of-week year`) |
| `IsActive` | Soft disable |

Timezone for triggers: **Europe/Prague**. Invalid CRON is skipped.

Hourly at minute 0: **`0 0 * ? * * *`**. Spec `periodics[].cron` emits Scheduler + line + `PeriodicID` param (no separate site-wide YAML).

Admin: Scheduler portlet. Periodic edit shows assigned scheduler lines.

## Object Service & Webhook

**Tables:** `ObjectService`, `ObjectWebhook`

External HTTP/service integrations callable from workflow or templates.

## DB transfer

All listed parent tables are type **U** or **D** in [`data/transfer-tables.json`](../data/transfer-tables.json).
