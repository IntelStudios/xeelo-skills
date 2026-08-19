# Node.js GraphQL patterns (object action)

How-to for `CustomJS` in **Run Node.js (Last)**. Schema: [graphql.md](../docs/entities/graphql.md). Runtime / `Context`: [nodejs-esm.md](../docs/entities/nodejs-esm.md). Wiring: [add-object-action.md](add-object-action.md).

Replace `OBJECTCODE`, `FIELD_CODE`, `OTHERCODE`, `TEMPLATE_ID` with **site** codes and IDs from `env/` after `/download-db`.

## Before test

- [ ] GraphQL names match `env/objects/<slug>/spec/object.yaml` (`object.code`, `fields[].code`)
- [ ] Select reads `lines` (valueData), not `linesFormatted`
- [ ] Self-update: no `createType`, `withRefresh: false`
- [ ] `CREATE` only on a **different** object; `template` = `ObjectDefaultID`
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

## 4. Combine (CREATE + Select + self-update)

Typical import-style action:

1. Build payload (random, `fetch`, `Context.Variable`, …)
2. `CREATE` on the other object (pattern 2)
3. `Select_` this request’s `lines` (pattern 3)
4. Mutate this request with `withRefresh: false` (pattern 1)
5. `return` a short summary for the result memo

Do not `CREATE`/`UPDATE` **this** request. Do not use `linesFormatted` for the arithmetic.
