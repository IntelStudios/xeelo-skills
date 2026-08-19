# Node.js object action (ESM)

How to write **Run Node.js (Last)** scripts (`CustomJS`) for `ObjectAction`. Entity wiring: [object-actions.md](object-actions.md). GraphQL schema: [graphql.md](graphql.md). Recipes: [add-object-action.md](../../recipes/add-object-action.md), [nodejs-graphql-patterns.md](../../recipes/nodejs-graphql-patterns.md).

Runtime: `POST /execute-esm`. Platform template: `spEndPointRunNodeJSMainDefault`.

## Defaults (always ESM)

New Node.js object actions in this KB are **ESM**. Do not emit legacy (non-ESM) `CustomJS`.

| Spec param | Default | Why |
|------------|---------|-----|
| `typeCode` | `spEndPointRunNodeJSMainLast` | Runs in the second execute pass (`IsLast=1`) |
| `EndPointRunESM` | `"1"` | `POST /execute-esm` (not the old evaluate path) |
| `EndPointRunWait` | `"1"` | Wait and write `main()` return value onto the request |
| `EndPointRunTimeout` | `"60000"` | Wall-clock ms |
| `ApplicableEventType` | `"Save,SaveNew"` (or include `WorkflowAction`) | Restricts when the action runs |
| `CustomJS` | named `export async function main()` | Platform default template |

```javascript
import { XeeloGraphQLClient } from "@xeelo/graphql-client";

export async function main() {
    const client = new XeeloGraphQLClient();
    // …
    return "OK";
}
```

Script rules (runtime-enforced):

- Export **exactly one** function, no parameters — `export async function main()` (named `main` is the platform default; `export default` also works)
- Return value is optional; it becomes the HTTP response body (`EndPointRunResponseText`)
- `log.error()` / `console.error()` marks the run as **failed** even if `main()` returns
- `require()` / `eval()` / arbitrary imports fail. Allowlist + `// install("pkg")` only

## Context

Injected global. Built by `spEnPointRunNodeJSCreateContext` for the request the action is handling. In Node.js ESM use **dot access** (`Context.RequestID`), not dict keys.

### Event and request

| Field | Type | Description |
|-------|------|-------------|
| `EventType` | string | Why the script is running |
| `RequestID` | number | Request this action is executing on |
| `RequestStatus` | `{ ID, Name }` | Current status |
| `RequestIsSubmitted` | boolean | Submitted flag |

`EventType` is one of: `WorkflowAction`, `Save`, `SaveNew`, `WorkflowFail`, `WorkflowUpdate`, `WorkflowRecall`, `ExportFail`, `Periodic`.

### Object and role

| Field | Type | Description |
|-------|------|-------------|
| `Role` | `{ ID, Name }` | Role under which the script runs |
| `Object` | `{ ID, Name }` | Business object of the request |
| `ObjectDefault` | `{ ID, Name }` | Template |
| `ObjectUpdateAction` | `{ ID, Name }` (optional) | Present when an update action triggered the run |

### Audit

Each of these has `Date` and `UserName` (optional groups omitted when not set):

| Field | Description |
|-------|-------------|
| `Created` | Request created |
| `Modified` | Last modification |
| `Cancelled` | Cancellation |
| `LastWorkflow` | Last workflow step |
| `LastWorkflowAction` | `{ ID, Name }` — last workflow action |

### GraphQL

| Field | Type | Description |
|-------|------|-------------|
| `GraphQL.URL` | string | GraphQL endpoint (site typically `http://xeelo-graphql/graphql`) |
| `GraphQL.Token` | string | **Service account ID 0** bearer token |

`XeeloGraphQLClient` construction **fails** if `URL` or `Token` is missing. The token is **service account ID 0**, not the interactive user. Grant **WRITE** in Admin on **every** object the script mutates (`UserAccess` is not in transfer). See [users-and-access.md](users-and-access.md).

### Variables

`Context.Variable` is a map of active **General Variables**, keyed by variable **code** (must be a valid JS identifier):

```javascript
const apiUrl = Context.Variable?.MyApiUrl;
```

### Other globals (no import)

`log` / `console` (`trace`, `debug`, `info`, `warn`, `error`), `fetch`, `FormData`, `File`, `Blob`, `Buffer`, `sleep(ms)`, `Promise`, `AbortSignal`.

## XeeloGraphQLClient

Virtual module (not npm). Reads `Context.GraphQL` on construction.

```javascript
import { XeeloGraphQLClient } from "@xeelo/graphql-client";

const client = new XeeloGraphQLClient();
await client.request(document, variables?);
await client.query(query, variables?, returnAll?); // paginate when returnAll and query has $limit / $offset
```

## Resolve names from env

GraphQL identifiers are `sanitizeGraphQLName` of **site** codes after `/download-db`, not whatever the original spec used if they diverged.

| From env | Used as |
|----------|---------|
| `object.code` | `Select_{code}`, `Mutate_{code}`, input `Mutate{code}Input` |
| `fields[].code` | `lines.{code}` (Select and Mutate) |
| `ids.explicit.objectDefaultId` / `templates.*` | `template` on `CREATE` |

Full naming, query args, `createType` variants, and **`lines` vs `linesFormatted`**: [graphql.md](graphql.md).

**Select current lines** — read `lines` (valueData), never `linesFormatted`, when the script will compute or write the value:

```javascript
const selectData = await client.request(
    `query ($requestIds: [Int!]) {
        Select_OBJECTCODE(requestIds: $requestIds) {
            lines { FIELD_CODE }
        }
    }`,
    { requestIds: [Context.RequestID] }
);
const current = parseFloat(
    selectData?.Select_OBJECTCODE?.[0]?.lines?.FIELD_CODE ?? "0"
) || 0;
```

## Mutating the current request — no refresh

The object action already runs **inside** `spRequestRefreshGeneral`. A nested `spRequestRefresh` on **`Context.RequestID`** re-enters object actions. Last types still see the button value `1` → loop / timeout.

**When mutating the request the action is currently handling, do not trigger refresh in the mutation.**

| Target | Shape | Re-runs **this** action? |
|--------|-------|--------------------------|
| **This** request | `{ requestId, withRefresh: false, lines }` — omit `createType` | No — `spRequestUpdate` only |
| This request + `withRefresh: true` | loop | Yes |
| This request + any `createType` | refresh always appended | Yes |
| **Other** object `CREATE` | `{ createType: "CREATE", template: ObjectDefaultID, lines }` | No (refresh is on the **new** request) |
| Other request update | `withRefresh` optional | Only if that other request’s actions re-enter this one |
| `withRefreshCache: true` | cache / message broker | No |

Safe self-update:

```javascript
import { XeeloGraphQLClient } from "@xeelo/graphql-client";

export async function main() {
    const client = new XeeloGraphQLClient();
    const value = String(/* computed */);

    const data = await client.request(
        `mutation ($input: [MutateOBJECTCODEInput!]!) {
            Mutate_OBJECTCODE(input: $input) {
                requestId
                success
                messages { procedure msgType msgText }
            }
        }`,
        {
            input: [{
                requestId: Context.RequestID,
                withRefresh: false,
                lines: { FIELD_CODE: value },
            }],
        }
    );

    const row = data?.Mutate_OBJECTCODE?.[0];
    if (!row?.success) {
        log.error(JSON.stringify(row?.messages ?? data));
        return;
    }
    return value;
}
```

Replace `OBJECTCODE` / `FIELD_CODE` with sanitized site codes from env. **Omit `createType`.** Set `withRefresh: false` explicitly so a later edit cannot flip the default.

If a **button** gated the action (`equals_text` / `1`), that line stays `1` after save. Later Save events will run the action again unless the same mutation clears the button (e.g. `BUTTON_CODE: ""`).

`main()` return value (with `EndPointRunWait: "1"`) writes to `ResponseTextObjectLineID` (use a memo). GraphQL `lines` writes are separate — both can be used in one script.

## CREATE another object

`createType: CREATE` on a **different** object is allowed from this action. Refresh of the new request does not re-enter the current object’s Last action. `template` is `ObjectDefaultID` from `ids.explicit.objectDefaultId` or `ids.explicit.templates.<key>`.

```javascript
const txData = await client.request(
    `mutation ($input: [MutateOTHERCODEInput!]!) {
        Mutate_OTHERCODE(input: $input) {
            requestId
            success
            messages { procedure msgType msgText }
        }
    }`,
    {
        input: [{
            createType: "CREATE",
            template: TEMPLATE_ID,
            lines: { OTHER_FIELD: amount },
        }],
    }
);

const txRow = txData?.Mutate_OTHERCODE?.[0];
if (!txRow?.success) {
    log.error(JSON.stringify(txRow?.messages ?? txData));
    return;
}
return `created #${txRow.requestId}`;
```

Grant **WRITE** for service account `0` on **OTHERCODE** (CREATE) as well as on this object (self-update). Combined Select → CREATE → self-update: [nodejs-graphql-patterns.md](../../recipes/nodejs-graphql-patterns.md).
