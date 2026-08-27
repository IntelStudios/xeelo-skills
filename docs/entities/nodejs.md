# Node.js object action

How to write **Run Node.js (Last)** scripts (`CustomJS`) for `ObjectAction`. Entity wiring: [object-actions.md](object-actions.md). GraphQL schema: [graphql.md](graphql.md). Recipes: [add-object-action.md](../../recipes/add-object-action.md), [nodejs-graphql-patterns.md](../../recipes/nodejs-graphql-patterns.md).

Runtime: `POST /execute`. Platform template: `spEndPointRunNodeJSMainDefault`. Scripts are **always ESM**.

## Defaults

| Spec param | Default | Why |
|------------|---------|-----|
| `typeCode` | `spEndPointRunNodeJSMainLast` | Runs in the second execute pass (`IsLast=1`) |
| `EndPointRunWait` | `"1"` | `"1"` wait and write `main()` return onto the request. `"0"` fire-and-forget (message broker still runs the ESM; raise `EndPointRunTimeout` for long jobs) |
| `EndPointRunTimeout` | `"60000"` | Wall-clock ms. Raise for bulk CREATE (import) |
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
- `logs` in the execute JSON stays empty unless the script calls `log.error()` / `console.error()`. Those also set `success: false` even if `main()` returns
- Missing optional config (empty API key) can return a user message **without** `log.error`
- External HTTP failures: `log.error` with status + response body; **do not** log tokens or URLs that contain a token
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

YAML, JWT, AWS, Azure, lodash, Puppeteer, and the rest of the libraries below are **not** globals — `import` them from the [built-in allowlist](#built-in-imports) or after [`// install`](#install-directive).

## Built-in imports

You may `import` these specifiers without `// install`. Anything else fails unless declared with `// install`.

| Import specifier | Typical import | Notes |
|------------------|----------------|-------|
| `"node-fetch"` | `import fetch from "node-fetch"` | Also exports `FormData`, `File`. `fetch` is a global too; use `AbortSignal.timeout()` for request timeouts |
| `"js-yaml"` | `import yaml from "js-yaml"` | `yaml.load()` / `yaml.dump()` |
| `"pdf-lib"` | `import pdfLib from "pdf-lib"` | PDF create / edit |
| `"exceljs"` | `import ExcelJS from "exceljs"` | Spreadsheet read/write |
| `"fast-xml-parser"` | `import { XMLParser, XMLBuilder } from "fast-xml-parser"` | XML parse and build |
| `"jsonwebtoken"` | `import jwt from "jsonwebtoken"` | JWT sign and verify |
| `"node:crypto"` | `import crypto from "node:crypto"` | Node.js crypto |
| `"decimal.js"` | `import Decimal from "decimal.js"` | Arbitrary-precision decimals |
| `"lodash"` | `import _ from "lodash"` | Utilities |
| `"aws-sdk"` or `"@aws-sdk/client-s3"` | `import * as aws from "@aws-sdk/client-s3"` | Both resolve to the same S3 SDK |
| `"aws4"` | `import aws4 from "aws4"` | AWS request signing |
| `"@azure/identity"` | `import * as identity from "@azure/identity"` | Azure auth |
| `"@azure/storage-blob"` | `import * as storageBlob from "@azure/storage-blob"` | Blob storage |
| `"@azure/arm-costmanagement"` | `import * as costManagement from "@azure/arm-costmanagement"` | Cost management |
| `"@azure/arm-cognitiveservices"` | `import * as cognitiveServices from "@azure/arm-cognitiveservices"` | Cognitive services |
| `"@azure/openai"` | `import * as openai from "@azure/openai"` | Azure OpenAI |
| `"@azure/arm-maps"` | `import * as maps from "@azure/arm-maps"` | Azure Maps |
| `"@azure/arm-botservice"` | `import * as botService from "@azure/arm-botservice"` | Bot Service |
| `"puppeteer"` | `import puppeteer from "puppeteer"` | Headless Chromium. Runtime adds `--no-sandbox`. Headful (`headless: false`) fails. Close the browser (or the runtime will close leftover browsers and warn) |
| `"@xeelo/graphql-client"` | `import { XeeloGraphQLClient } from "@xeelo/graphql-client"` | Virtual module; reads `Context.GraphQL` |

Prefer the allowlist when the package is already there.

## Install directive

Use `// install("package-name")` in a **comment** to pull an extra npm package before the module runs, then `import` it as usual.

| Form | Example |
|------|---------|
| Line comment | `// install("dayjs")` |
| Block comment | `/* install("uuid@9.0.1") */` |
| Version pin | `install("openai@4.3.1")` |

Rules:

- The directive must be **inside a comment**. Bare `install("uuid")` in code is ignored and the import fails.
- Multiple directives are allowed; duplicates are deduplicated.
- Subpath imports work after the root package is installed (`import "dayjs/locale/cs"` after `// install("dayjs")`).
- Install is scoped to **this** object action or periodic action (`ScopeID`). Another action does not see those packages even with the same script text. The same action reuses what it already installed; the first run is slower.

```javascript
// install("dayjs")
import dayjs from "dayjs";

export async function main() {
    return dayjs().format("YYYY-MM-DD");
}
```

**Native addons do not work.** The Node runtime runs in a Docker image without a compiler. Packages that compile native code (`node-gyp`) and JS wrappers over native dependencies fail at `// install`. Use the allowlist or a pure-JS package.

Import resolution: packages installed for this action → allowlist → `Cannot import module <specifier>`.

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

Full naming, query args, `createType` variants, **`lines` vs `linesFormatted`**, date `dd-MM-yyyy`, and `lineFilters`: [graphql.md](graphql.md).

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

## Mutating the current request — no refresh (ObjectAction only)

This rule is **ObjectAction** (`EventType` Save / SaveNew / WorkflowAction / …). It does **not** apply to Periodic Node.js — there you **must** refresh; see [below](#periodic--graphql-mutate-must-refresh).

The object action already runs **inside** `spRequestRefreshGeneral`. A nested `spRequestRefresh` on **`Context.RequestID`** re-enters object actions. Last types still see the button value `1` → loop / timeout.

**When mutating the request the ObjectAction is currently handling, do not trigger refresh in the mutation.**

| Target | Shape | Re-runs **this** action? |
|--------|-------|--------------------------|
| **This** request | `{ requestId, withRefresh: false, lines }` — omit `createType` | No — `spRequestUpdate` only |
| This request + `withRefresh: true` | loop | Yes |
| This request + any `createType` | refresh always appended | Yes |
| **Other** object `CREATE` | `{ createType: "CREATE", template: ObjectDefaultID, lines }` | No (refresh is on the **new** request) |
| Other request update | `withRefresh` optional | Only if that other request’s actions re-enter this one |
| Other request **refresh only** | `{ requestId, withRefresh: true }` — omit `lines` and `createType` | Runs Last on **that same** request if refresh still executes there. Do **not** use on `Context.RequestID`. **Completed** requests: use `UPDATE` below instead |
| Other **completed** request + update action | `{ requestId, createType: "UPDATE", updateAction }` — omit `lines` | No on this action. Starts `spRequestInsert` RequestTypeID 2 (new version, copied lines); refresh runs on the **new** request. `UPDATE_EMPTY` skips copied lines |
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

## Periodic — GraphQL mutate must refresh

A Periodic Node.js action (`EventType = Periodic`) does **not** run inside `spRequestRefreshGeneral`. Line writes with the ObjectAction self-update shape (`withRefresh: false`, no `createType`) persist values but **do not** run Last / calculations / object actions on that request.

**From Periodic JS, every GraphQL mutate that changes a request must trigger refresh** — `withRefresh: true` on a simple update, or a `createType` that always refreshes (`CREATE`, `UPDATE`, `UPDATE_EMPTY`). `withRefreshCache` is not enough. This is the opposite of ObjectAction on the current request.

| Intent | Shape |
|--------|--------|
| Edit lines on an **open** request (including `Context.RequestID` if it is still refreshable) | `{ requestId, withRefresh: true, lines }` — omit `createType` |
| Start an **update action** (completed request, new version + Last) | `{ requestId, createType: "UPDATE", updateAction }` — omit `lines`; refresh is on the **new** version |
| CREATE another object | `{ createType: "CREATE", template, lines }` — refresh is on the **new** request |

Do not copy ObjectAction `withRefresh: false` into Periodic `CustomJS`. Recipe: [add-periodic.md](../../recipes/add-periodic.md).

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

Grant **WRITE** for service account `0` on **OTHERCODE** (CREATE) as well as on this object (self-update). Combined Select → CREATE → self-update, including [batch + parallel CREATE](../../recipes/nodejs-graphql-patterns.md#6-batch--parallel-create).
