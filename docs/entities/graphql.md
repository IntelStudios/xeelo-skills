# GraphQL (objects)

How Xeelo builds the per-site GraphQL schema from object metadata. Use this when writing `CustomJS` for a Node.js object action, or any `Select_` / `Mutate_` call.

Runtime wiring from Node.js: [nodejs-esm.md](nodejs-esm.md). Patterns: [nodejs-graphql-patterns.md](../../recipes/nodejs-graphql-patterns.md).

The schema is generated from the object model (`spGraphQLObjectModel`). After object/layout changes, **`/precompile`** so GraphQL picks up new codes and fields. After an Object Transfer, use **`/publish`** (real transfer + precompile).

## Sanitize names

Identifiers come from **site** `ObjectCode` / `ObjectLineCode` (after `/download-db`, see `env/objects/<slug>/spec/object.yaml`). `sanitizeGraphQLName`:

- spaces and specials → `_`
- consecutive `_` collapse
- leading/trailing `_` stripped
- if the result starts with a digit, prefix `_`

Take codes from env, not from an older spec if they diverged (`ACCOUNT` vs `object_9100_account`).

On **insert**, Admin often stores `ObjectLineCode` as `line_{ObjectLineID}_{slug}` even when the spec/`Object Transfer` sent a shorter `code` (`line_account` → `line_9142_account`). GraphQL `lines.{code}` is that stored code. After the first `/download-db`, rewrite `CustomJS` to match `env/objects/<slug>/spec/object.yaml` field codes before retesting.

For `code` = sanitized `ObjectCode`:

| Kind | GraphQL name |
|------|----------------|
| Query | `Select_{code}` |
| Mutation field | `Mutate_{code}` |
| Mutation input | `Mutate{code}Input` (no `_` after `Mutate`) |
| Lines input | `Mutate{code}LinesInput` |
| Request type | `{code}` |
| Query line types | `{code}Lines`, `{code}LinesFormatted` |
| Line filter input | `{code}LineFilter` |

Example: `object_9100_account` → `Select_object_9100_account`, `Mutate_object_9100_account`, input `Mutateobject_9100_accountInput`.

**SubGrid** uses the same prefixes from `subgrid.code`.

Other operations (one-line; not object-model generated the same way): `health`, `access_rights`, `Select_reference` / `Mutate_reference`, `Select_lookup` / `Mutate_lookup`, `Select_variable`, `select_attachment`, `Delete_request`, `Execute_Periodic`, plus **admin transfer / precompile** below. `Delete_request` is documented next.

## Query `Select_{code}`

```graphql
Select_OBJECTCODE(
  requestIds: [Int!]
  limit: Int
  offset: Int
  lineFilters: OBJECTCODELineFilter
  # plus one arg per filterable header, e.g. role, status, created
): [OBJECTCODE!]!
```

| Argument | Meaning |
|----------|---------|
| `requestIds` | Specific requests; omit to scan. From an object action: `[Context.RequestID]` |
| `limit` | Default 1000, max 10000 |
| `offset` | Skip N rows |
| `lineFilters` | Per-line conditions. Default `StringFilterCondition`; date line type **8** → `DateFilterCondition`; number type **12** → `NumberFilterCondition`. Filters **valueData** (`lines`), not formatted |
| Header args | Only headers with `isfilter != 0` (typical: `role`, `status`, `created`, …) |

Return type `{code}`:

- `requestId: Int!`
- dynamic **headers** (typed by header `type.id`: `1` Id, `2` IdName, `3` DateUser, `4` UserList, `5` JSON, `6` String)
- `lines: {code}Lines`
- `linesFormatted: {code}LinesFormatted`

## `lines` vs `linesFormatted`

Same keys (`sanitize(line.code)`), both `String` or null. Different DB columns:

| Field | DB | Meaning |
|-------|-----|---------|
| `lines.{code}` | `valueData` (`line_{id}_data`) | Stored value — reference **bind**, raw number, raw text. **Read this for calculations. Write this in mutations.** |
| `linesFormatted.{code}` | `valueFormat` (`line_{id}_format`) | Display — reference **label**, formatted number/date. JOINs load only when formatted is in the selection. **Read-only. Mutations do not accept formatted.** |

For Node.js arithmetic (balance += amount) always use `lines`, then `parseFloat` / write `String` or `.toFixed`. Use `linesFormatted` only for UI/export text.

## Date picker (type 8)

Stored **valueData** / GraphQL `lines.{code}` is **`dd-MM-yyyy`** (day-month-year with hyphens), e.g. `19-08-2026`. Empty is `""`. Save (`fnDateCheck`) parses with `cs-cz` and normalizes to that string.

Do **not** parse `lines` with `new Date(s)`. A hyphenated non-ISO string is treated as US `MM-dd-yyyy` in JavaScript: year can look right, month is wrong (`01-08-2026` → January, not August). Split `dd-MM-yyyy` (and only then, as a fallback, `yyyy-MM-dd` from ISO ingress) into calendar parts. Never use `getUTCMonth()`.

Mutations should **write** `dd-MM-yyyy`. Other `cs-cz`-parseable inputs are normalized on save.

`linesFormatted.{code}` is display (`fnDateString2`, site layout; often `dd.MM.yyyy`). Read-only; do not send it in `Mutate_`.

**Date `lineFilters`** use `DateFilterCondition` with values in **`YYYY-MM-DD`** (not the storage format). See below.

## `lineFilters`

Each filterable line is a field on `{code}LineFilter`. Type **8** → `DateFilterCondition`; type **12** → `NumberFilterCondition`; otherwise `StringFilterCondition`. Filters **valueData**, not formatted.

Operators are GraphQL enums (`EQ`, not `eq` / `equals`):

| Input | Operators | Value |
|-------|-----------|--------|
| `StringFilterCondition` | `EQ` `NE` `GT` `GTE` `LT` `LTE` `CONTAINS` `STARTS_WITH` `ENDS_WITH` `IN` `NOT_IN` `IS_EMPTY` `IS_NOT_EMPTY` | `value: String` (or `values` for IN) |
| `DateFilterCondition` | `EQ` `NE` `GT` `GTE` `LT` `LTE` `IN` `NOT_IN` `BETWEEN` `NOT_BETWEEN` | `value` / `from` / `to` as **`YYYY-MM-DD`** |
| `NumberFilterCondition` | same scalar set as date | `value: Float` |

Look up a **refObject** row from a combo bind (exact match on the bind line):

```graphql
Select_OTHERCODE(
  lineFilters: { BIND_FIELD: { operator: EQ, value: $bind } }
  limit: 1
) { lines { NAME_FIELD } }
```

`$bind` is `lines.COMBO_FIELD` on the current request (valueData), not `linesFormatted` (label).

## Mutation `Mutate_{code}`

```graphql
Mutate_OBJECTCODE(input: [MutateOBJECTCODEInput!]!): [MutationResponse]!
```

Each array element is processed separately (`processSingleMutate`). There is **no** application transaction across the batch — a later item can fail after earlier items committed. `CREATE` always refreshes the **new** request, so a large `input` array is still sequential wall-clock on that one HTTP call (including nested object actions). For bulk import, keep each array modest and run several `client.request` calls concurrently — [nodejs-graphql-patterns.md](../../recipes/nodejs-graphql-patterns.md#6-batch--parallel-create).

`MutationResponse`: `requestId`, `requestSubId`, `userId`, `success`, `messages { procedure, msgType, msgText }`. `success` is false when any message has `MsgType = DANGER`.

### Input fields

| Field | Role |
|-------|------|
| `requestId` | Optional for `CREATE`; required for simple update and `UPDATE` / `UPDATE_EMPTY` |
| `userLogin` / `userId` | Resolve `@UserID`. If both omitted, **`0`** (service account) |
| `createType` | `CREATE` \| `UPDATE` \| `UPDATE_EMPTY` — omit for simple update |
| `template` | `ObjectDefaultID`; **required** when `createType: CREATE` |
| `updateAction` | `ObjectUpdateActionID`; **required** when `UPDATE` / `UPDATE_EMPTY` |
| Headers | Updateable headers sit **on the input**, not under `header { }`. UserList (type 4) is `[Int!]`; `owner` / `watcher` use `UserListUpdateInput` |
| `lines` | `Mutate{code}LinesInput` — each field `String`; attachment type **9** is `AttachmentInput` |
| `withRefresh` | Default `false`. Nested `spRequestRefresh` |
| `withRefreshCache` | Default `false`. Cache / message broker only — does **not** re-run object actions |

### Variants

| Shape | Required | Calls `spRequestRefresh`? |
|-------|----------|---------------------------|
| Simple update (no `createType`) | `requestId` + `lines` and/or headers | Only if `withRefresh: true` |
| `CREATE` | `template`; `requestId` optional | **Always** |
| `UPDATE` | `updateAction` + `requestId` | **Always** (on the **new** version) |
| `UPDATE_EMPTY` | `updateAction` + `requestId` | **Always** (on the **new** version; header only — no copied lines) |
| Simple update + `withRefresh: true` | `requestId` (lines optional) | **Yes** on **that** request — does **not** start an update action. Not enough when the request is **Completed** and Last actions need a new version |

`createType: UPDATE` is GraphQL for the UI update action: `spRequestInsert` `@RequestTypeID = 2` with `@UpdateRequestID` + `@ObjectUpdateActionID`. It copies line data onto a **new** request (same `RequestCode`) and then refreshes that new row, so Last object actions run there. Omit `lines` unless you must override copied values. Use `UPDATE_EMPTY` (`RequestTypeID` 3) only when Last does not need the copied lines.

`withRefresh: true` without `createType` calls `spRequestRefresh` on the **existing** `requestId`. Completed requests typically do not re-enter the same Last path as an update action.

Pipeline: optional `spRequestInsert` (`createType`) → uniqueness checks for lines whose `ObjectLineUniqueID` is set (GraphQL model `unique: 1`) → `spRequestUpdate` per line → headers (priority, owner/watcher, workflow) → refresh if `createType` or `withRefresh` → optional cache refresh. Unique levels and autonumber identifiers: [object-model.md](object-model.md#unique).

From a Node.js **object action on the current request**, use **simple update** only (`withRefresh: false`, no `createType`). `CREATE` / `UPDATE` on a **different** object or request may refresh. See [nodejs-esm.md](nodejs-esm.md#mutating-the-current-request--no-refresh).

## Mutation `Delete_request`

Deletes whole requests (not line values). Separate from `Mutate_`. Needs GraphQL **DELETE** on that object (`objects.delete`); **WRITE** is not enough. Check with `access_rights { id code canRead canWrite canDelete }`.

```graphql
Delete_request(objectId: Int!, requestIds: [Int!]!, userLogin: String, userId: Int): [MutationResponse!]
```

| Argument | Role |
|----------|------|
| `objectId` | Numeric object id (`env/catalog.yaml` `objects[].id`, e.g. Transakce `9003`) — not the GraphQL code |
| `requestIds` | Requests to delete; at least one. Each id is `spRequestDelete` in its **own** DB transaction |
| `userLogin` / `userId` | Resolve `@UserID`. If both omitted, **`0`** |

Returns one `MutationResponse` per id (`requestId`, `success`, `messages`). A failed id does not stop the rest of the array.

Public HTTP is `POST {SiteServerAddress}/graphql` with `Authorization: Bearer <token>`. Select ids with `Select_{code}` (`limit` default 1000, max 10000, paginate with `offset`), then delete in modest `requestIds` batches.

## Admin transfer and precompile

Fixed operations, **not** bound to an object. They require a GraphQL token with **`isAdmin`**. Object READ/WRITE/DELETE is not checked. XeeloKB connection is `{ xeeloUrl, token }` — `POST {xeeloUrl}/graphql`. SQL timeout is **10 minutes**. XML between GraphQL string and SQL `varbinary` is **UTF-16 LE**.

| Operation | Skill | Role |
|-----------|-------|------|
| `Select_admin_transfer_download { xml }` | `/download-db` | Whole-site DB-transfer XML |
| `Mutate_admin_transfer_upload(fileName, xml)` | dry-run after generate; `/publish` | Insert Object Transfer; returns `objectSetupXmlId` |
| `Mutate_admin_transfer_process(id, isTestOnly)` | dry-run (`true`); `/publish` (`false`) | Apply or dry-run the uploaded transfer |
| `Mutate_admin_precompile` | `/publish` (after process) and `/precompile` | Rebuild settings cache; GraphQL process **may restart** |

After precompile, wait until `{xeeloUrl}/graphql-api/health` (or `query { health }`) responds again.

```graphql
query { Select_admin_transfer_download { xml } }

mutation ($fileName: String!, $xml: String!) {
  Mutate_admin_transfer_upload(fileName: $fileName, xml: $xml) { objectSetupXmlId }
}

mutation ($id: Int!, $isTestOnly: Boolean!) {
  Mutate_admin_transfer_process(id: $id, isTestOnly: $isTestOnly) {
    success
    messages { procedure msgType msgText }
  }
}

mutation {
  Mutate_admin_precompile {
    success
    messages { procedure msgType msgText }
  }
}
```

`isTestOnly: true` verifies the package without applying it (loop dry-run). `/publish` uploads again with `isTestOnly: false`, then precompiles. Use `/precompile` when the transfer is already on the site.
