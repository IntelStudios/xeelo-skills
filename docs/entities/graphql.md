# GraphQL (objects)

How Xeelo builds the per-site GraphQL schema from object metadata. Use this when writing `CustomJS` for a Node.js object action, or any `Select_` / `Mutate_` call.

Runtime wiring from Node.js: [nodejs-esm.md](nodejs-esm.md). Patterns: [nodejs-graphql-patterns.md](../../recipes/nodejs-graphql-patterns.md).

The schema is generated from the object model (`spGraphQLObjectModel`). After object/layout changes, **`/publish`** (PreCompileSettings) so GraphQL picks up new codes and fields.

## Sanitize names

Identifiers come from **site** `ObjectCode` / `ObjectLineCode` (after `/download-db`, see `env/objects/<slug>/spec/object.yaml`). `sanitizeGraphQLName`:

- spaces and specials → `_`
- consecutive `_` collapse
- leading/trailing `_` stripped
- if the result starts with a digit, prefix `_`

Take codes from env, not from an older spec if they diverged (`ACCOUNT` vs `object_9100_account`).

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

Other operations (one-line; not object-model generated the same way): `health`, `access_rights`, `Select_reference` / `Mutate_reference`, `Select_lookup` / `Mutate_lookup`, `Select_variable`, `select_attachment`, `Delete_request`, `Execute_Periodic`.

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

## Mutation `Mutate_{code}`

```graphql
Mutate_OBJECTCODE(input: [MutateOBJECTCODEInput!]!): [MutationResponse]!
```

Each array element is processed separately (`processSingleMutate`). There is **no** application transaction across the batch — a later item can fail after earlier items committed.

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
| `UPDATE` | `updateAction` + `requestId` | **Always** |
| `UPDATE_EMPTY` | `updateAction` + `requestId` | **Always** |

Pipeline: optional `spRequestInsert` (`createType`) → `spRequestUpdate` per line → headers (priority, owner/watcher, workflow) → refresh if `createType` or `withRefresh` → optional cache refresh.

From a Node.js **object action on the current request**, use **simple update** only (`withRefresh: false`, no `createType`). `CREATE` / `UPDATE` on a **different** object or request may refresh. See [nodejs-esm.md](nodejs-esm.md#mutating-the-current-request--no-refresh).
