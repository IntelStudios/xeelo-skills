# Node.js GraphQL patterns (object action)

How-to for `CustomJS` in **Run Node.js (Last)**. Schema: [graphql.md](../docs/entities/graphql.md). Runtime / `Context`: [nodejs-esm.md](../docs/entities/nodejs-esm.md). Wiring: [add-object-action.md](add-object-action.md).

Replace `OBJECTCODE`, `FIELD_CODE`, `OTHERCODE`, `TEMPLATE_ID` with **site** codes and IDs from `env/` after `/download-db`.

## Before test

- [ ] GraphQL names match `env/objects/<slug>/spec/object.yaml` (`object.code`, `fields[].code`) — after first insert this is often `line_{id}_{slug}`, not the short spec `code` you wrote before deploy
- [ ] External HTTP failures: `log.error` status + body (no tokens/URLs); empty optional config = message without `log.error`
- [ ] Select reads `lines` (valueData), not `linesFormatted`
- [ ] Date picker `lines` are `dd-MM-yyyy` — split the string, do not use `new Date(s)`
- [ ] ObjectAction self-update: no `createType`, `withRefresh: false`
- [ ] Periodic GraphQL mutate: **must refresh** (`withRefresh: true` or `createType` CREATE/UPDATE) — [nodejs-esm.md](../docs/entities/nodejs-esm.md#periodic--graphql-mutate-must-refresh)
- [ ] `CREATE` only on a **different** object; `template` = `ObjectDefaultID`
- [ ] Bulk CREATE: several items per `input` array **and** a small pool of concurrent `client.request` calls; raise `EndPointRunTimeout` — [§6](#6-batch--parallel-create)
- [ ] Refresh **open** other requests: `withRefresh: true` without `lines`; batch + pool — [§7](#7-refresh-other-requests-in-parallel-no-line-writes)
- [ ] **Completed** other requests that need Last (tags, titles): `createType: UPDATE` + `updateAction`, no `lines` — [§8](#8-start-update-action-on-completed-requests)
- [ ] Service account **0** has **WRITE** on every mutated object ([users-and-access.md](../docs/entities/users-and-access.md))
- [ ] Button (if used) is **WorkflowStepAccess editable** on the step
- [ ] Clear the button in the same self-update if the action must not re-run on the next Save

## 1. Self-update (this request)

Omit `createType`. Set `withRefresh: false`. Numbers as `String`.

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

`main()` return (with wait) lands on `ResponseTextObjectLineID`. GraphQL `lines` writes are separate.

## 2. CREATE another object

`createType: CREATE` + `template` is fine because refresh runs on the **new** request.

```javascript
const created = await client.request(
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

const txRow = created?.Mutate_OTHERCODE?.[0];
if (!txRow?.success) {
    log.error(JSON.stringify(txRow?.messages ?? created));
    return;
}
```

Use `txRow.requestId` in the return string. Grant WRITE for user `0` on **OTHERCODE**.

## 3. Select → compute → self-update

Read current `lines`, then write without refresh.

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
const next = (current + parseFloat(amount)).toFixed(2);
```

Then the self-update from pattern 1 with `FIELD_CODE: next`.

Date picker `lines` are **`dd-MM-yyyy`**. Split that string; do not use `new Date(s)`. [graphql.md](../docs/entities/graphql.md#date-picker-type-8).

## 4. Combine (CREATE + Select + self-update)

Typical import-style action:

1. Build payload (random, `fetch`, `Context.Variable`, …)
2. `CREATE` on the other object (pattern 2). For many rows use batch + limited parallel (pattern 6)
3. `Select_` this request’s `lines` (pattern 3)
4. Mutate this request with `withRefresh: false` (pattern 1)
5. `return` a short summary for the result memo

Do not `CREATE`/`UPDATE` **this** request. Do not use `linesFormatted` for the arithmetic.

## 5. Lookup refObject by combo bind

Combo `lines.COMBO_FIELD` is the **bind** (e.g. account number), not the display label. Select the other object with `lineFilters` `EQ` on that bind line — do not page through all rows.

```javascript
const bind = String(txLines.COMBO_FIELD ?? "").trim();
let name = "";
if (bind) {
    const acc = await client.request(
        `query ($bind: String) {
            Select_OTHERCODE(
                lineFilters: { BIND_FIELD: { operator: EQ, value: $bind } }
                limit: 1
            ) { lines { NAME_FIELD } }
        }`,
        { bind }
    );
    name = String(acc?.Select_OTHERCODE?.[0]?.lines?.NAME_FIELD ?? "").trim();
}
```

Date `lineFilters` take **`YYYY-MM-DD`**, not `dd-MM-yyyy`. Operators are `EQ` (enum), not `eq` / `equals`. [graphql.md](../docs/entities/graphql.md#linefilters).

Use the same `lineFilters` when an import must skip already-stored keys — do not page through every request of the target object.

## 6. Batch / parallel CREATE

`Mutate_OTHERCODE(input: [MutateOTHERCODEInput!]!)` already takes an **array**. The GraphQL server still walks that array **one item at a time** (`processSingleMutate`). There is no all-or-nothing transaction: earlier `CREATE`s stay if a later item fails. Each `CREATE` **always** refreshes the **new** request, so nested Node.js Last actions on that object run inside the same HTTP call.

For import throughput, combine both:

| Lever | Why |
|-------|-----|
| Several `CREATE` items in one `input` | Fewer GraphQL round-trips |
| Modest batch size (about **10**) | One HTTP call must not sit behind N nested refreshes until the GraphQL/HTTP timeout |
| A few concurrent `client.request` calls (about **5**) | Overlaps CREATE+refresh across requests. Unbounded `Promise.all` per row overloads GraphQL/SQL |
| Higher `EndPointRunTimeout` | Parent Run Node.js Last default is `60000` ms — too short for a 90-day import |

Build the `CREATE` payloads first (dedupe keys in memory), then:

```javascript
const CREATE_BATCH = 10;
const CREATE_CONCURRENCY = 5;

function chunk(items, size) {
    const out = [];
    for (let i = 0; i < items.length; i += size) out.push(items.slice(i, i + size));
    return out;
}

async function mapPool(items, concurrency, fn) {
    const results = new Array(items.length);
    let next = 0;
    async function worker() {
        while (next < items.length) {
            const idx = next;
            next += 1;
            results[idx] = await fn(items[idx], idx);
        }
    }
    const n = Math.min(Math.max(concurrency, 1), items.length);
    await Promise.all(Array.from({ length: n }, () => worker()));
    return results;
}

const batches = chunk(creates, CREATE_BATCH);
const results = await mapPool(batches, CREATE_CONCURRENCY, async (batch) => {
    const created = await client.request(
        `mutation ($input: [MutateOTHERCODEInput!]!) {
            Mutate_OTHERCODE(input: $input) {
                requestId
                success
                messages { procedure msgType msgText }
            }
        }`,
        { input: batch }
    );
    const rows = created?.Mutate_OTHERCODE ?? [];
    let ok = 0;
    for (let i = 0; i < batch.length; i++) {
        if (!rows[i]?.success) {
            log.error(JSON.stringify(rows[i]?.messages ?? created));
            return { ok, error: true };
        }
        ok += 1;
    }
    return { ok, error: false };
});
```

Count `ok` across batches. Wait until **all** in-flight batches finish before the parent self-update / `return`. On partial failure, skip the parent-object balance write that assumes a full import; a re-run should skip already-created keys (`lineFilters` + in-memory `Set`). A failed item does not roll back earlier CREATEs. Schema: [graphql.md](../docs/entities/graphql.md#mutation-mutate_code).

## 7. Refresh other requests in parallel (no line writes)

To re-run **another open** request’s object actions on the **same** version (tags, titles, …) after this request changed shared data, mutate those request IDs with `withRefresh: true` and **omit `lines`**. Do not refresh `Context.RequestID`.

This is `spRequestRefresh` only. It does **not** start an [update action](../docs/entities/update-actions.md). If the targets are **Completed** and Last does not run on refresh, use [§8](#8-start-update-action-on-completed-requests).

Same batch + pool as §6. Set `EndPointRunWait: "0"` on this action if the user must not wait; still raise `EndPointRunTimeout`. Gate with `Context.ObjectUpdateAction` when the workflow step is shared with create.

```javascript
const REFRESH_BATCH = 10;
const REFRESH_CONCURRENCY = 5;

const ids = [...new Set(requestIds)];
const batches = chunk(
    ids.map((requestId) => ({ requestId, withRefresh: true })),
    REFRESH_BATCH
);
await mapPool(batches, REFRESH_CONCURRENCY, async (batch) => {
    const data = await client.request(
        `mutation ($input: [MutateOTHERCODEInput!]!) {
            Mutate_OTHERCODE(input: $input) {
                requestId
                success
                messages { procedure msgType msgText }
            }
        }`,
        { input: batch }
    );
    for (const row of data?.Mutate_OTHERCODE ?? []) {
        if (!row?.success) log.error(JSON.stringify(row?.messages ?? data));
    }
});
```

Find targets with `Select_OTHERCODE` + `lineFilters` `EQ` on the bind (two queries if the value can sit on either of two lines). Paginate with `client.query(..., true)` (`$limit` / `$offset`). `withRefreshCache` does **not** re-run object actions.

## 8. Start update action on completed requests

Completed requests need `spRequestInsert` `@RequestTypeID = 2` (copy lines, new version), not a refresh of the finished row. GraphQL: `createType: "UPDATE"` + `updateAction` (`ObjectUpdateActionID` from env `ids.explicit.updateActions.<key>`). Omit `lines` so the new version keeps copied data; Last then runs on the **new** `requestId`. Do **not** use `UPDATE_EMPTY` when Last reads those lines.

From an **ObjectAction** on the current request, do **not** use this on `Context.RequestID` (self-update is simple mutate, `withRefresh: false`). From a **Periodic** Node.js action (`EventType = Periodic`), `Context.RequestID` **is** the completed batch entity — call `UPDATE` on that id. See [add-periodic.md](add-periodic.md).

Each item creates a **new request version** (same `RequestCode`). Same batch + pool as §6. `EndPointRunWait: "0"` if the user must not wait. User **0** needs WRITE on the target object; the `updateAction` id must exist on that object.

This `UPDATE` + `updateAction` pattern can run from an **ObjectAction on another object** (find completed requests with `Select_` + `lineFilters`, then mutate). Gate with `Context.ObjectUpdateAction` when the step is shared with create, or with a type-18 button condition (`equals_text` param `1`) when a workflow button on that other object should start the versions.

```javascript
const UPDATE_BATCH = 10;
const UPDATE_CONCURRENCY = 5;
const OTHER_UPDATE_ACTION = UPDATE_ACTION_ID;

const ids = [...new Set(requestIds)];
const batches = chunk(
    ids.map((requestId) => ({
        requestId,
        createType: "UPDATE",
        updateAction: OTHER_UPDATE_ACTION,
    })),
    UPDATE_BATCH
);
await mapPool(batches, UPDATE_CONCURRENCY, async (batch) => {
    const data = await client.request(
        `mutation ($input: [MutateOTHERCODEInput!]!) {
            Mutate_OTHERCODE(input: $input) {
                requestId
                success
                messages { procedure msgType msgText }
            }
        }`,
        { input: batch }
    );
    for (const row of data?.Mutate_OTHERCODE ?? []) {
        if (!row?.success) log.error(JSON.stringify(row?.messages ?? data));
    }
});
```

Schema: [graphql.md](../docs/entities/graphql.md#mutation-mutate_code). Runtime table: [nodejs-esm.md](../docs/entities/nodejs-esm.md#mutating-the-current-request--no-refresh).

