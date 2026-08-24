# Add Periodic

Add a **Periodic** (batch on an object’s last-version requests) and optionally a **Scheduler** CRON that calls `spPeriodicExecute`.

Entity reference: [docs/entities/integrations.md](../docs/entities/integrations.md#periodic). Node.js: [docs/entities/nodejs-esm.md](../docs/entities/nodejs-esm.md). GraphQL update action: [nodejs-graphql-patterns.md](nodejs-graphql-patterns.md#8-start-update-action-on-completed-requests).

## Preconditions

- Object exists with layout + completed (or in-progress) requests matching `requestType`
- Target site has `PeriodicActionType` seed (including `spEndPointRunNodeJSMain`)
- Service account **0** has **WRITE** on every object the script mutates
- Bind Periodic to the object whose **requests** should run — not a child/import target

## Ask

Which object the Periodic hangs on (the batch entity). Default = the object whose update action / GraphQL mutate the script will call.

## Admin UI path

1. **Periodic** — name, object, request type, conditions, actions (type, params, action conditions)
2. **Scheduler** — CRON, line type `spPeriodicExecute`, param `PeriodicID`
3. Test: Periodic **Refresh**, or GraphQL `Execute_Periodic`, before waiting for Quartz

## Spec / Object Transfer path

Fragment `spec/periodics.yaml` (see [spec-format.md](../docs/transfer/spec-format.md#periodics-specperiodicsyaml)):

```yaml
periodics:
  - key: load_fio_hourly
    name: Load FIO transactions
    requestType: completed
    cron: "0 0 * ? * * *"
    conditions:
      - field: TYPE
        type: equals_text
        param1: FIO
    actions:
      - key: start_load_transactions
        name: Start load transactions
        typeCode: spEndPointRunNodeJSMain
        order: 10
        params:
          CustomJS: |
            import { XeeloGraphQLClient } from "@xeelo/graphql-client";
            export async function main() {
                const client = new XeeloGraphQLClient();
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
                            createType: "UPDATE",
                            updateAction: UPDATE_ACTION_ID,
                        }],
                    }
                );
                const row = data?.Mutate_OBJECTCODE?.[0];
                if (!row?.success) {
                    log.error(JSON.stringify(row?.messages ?? data));
                    return;
                }
                return String(row.requestId ?? "");
            }
          EndPointRunWait: "1"
          EndPointRunESM: "1"
          EndPointRunTimeout: "300000"
```

`cron` generates `Scheduler` + `SchedulerLine` (`spPeriodicExecute`) + `PeriodicID` param. Omit `cron` for on-demand only (`Execute_Periodic`).

Include in `xeelo-spec.yaml`:

```yaml
includes:
  - spec/object.yaml
  - spec/periodics.yaml
  - spec/language-table.yaml
  - spec/ids.yaml
```

Czech labels: `languageTable.periodics`, `periodicActions` (`periodicKey/actionKey`), `schedulers`.

Generate:

```bash
python scripts/generate-change-loop.py projects/<project>/changes/<slug>
```

**Transfer scope:** `Periodic`, `PeriodicCondition`, `PeriodicAction`, `PeriodicActionParam`, `PeriodicActionCondition`, `Scheduler`, `SchedulerLine`, `SchedulerLineParam`. **Not** action/condition type catalogs.

## Checklist

- [ ] Periodic `ObjectID` is the batch object (conditions shrink the request list)
- [ ] `requestType` matches whether those requests are completed (`completed` / `20`)
- [ ] Node.js type is `spEndPointRunNodeJSMain` (not `…Last`); ESM `EndPointRunESM: "1"`
- [ ] `EndPointRunWait: "1"` if later requests must not overlap (rate-limited HTTP)
- [ ] Raise `EndPointRunTimeout` for import / GraphQL UPDATE that runs Last
- [ ] GraphQL identifiers match **env** `object.code` / `ids.explicit.updateActions`
- [ ] Periodic GraphQL mutate **must refresh** (`withRefresh: true` or `createType` CREATE/UPDATE/UPDATE_EMPTY). ObjectAction on the current request must **not** ([nodejs-esm.md](../docs/entities/nodejs-esm.md#periodic--graphql-mutate-must-refresh))
- [ ] Periodic JS **may** `createType: UPDATE` on `Context.RequestID`; ObjectAction on the same request must not
- [ ] Service account 0 has WRITE
- [ ] `cron` is Quartz **7-field** (`0 0 * ? * * *` = hourly at :00, Europe/Prague)
- [ ] `languageTable` Czech for periodic / action / scheduler names
