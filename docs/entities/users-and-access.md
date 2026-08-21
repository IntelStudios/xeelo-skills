# Users and Access

User management vs DB transfer scope.

## Critical distinction

| Entity | In Admin UI | In DB transfer |
|--------|-------------|----------------|
| `User` | Yes | **No** |
| `UserAccess` | Yes | **No** |
| `UserDelegation` | Yes | **No** |
| `Role` | Yes | **Yes** |
| `RequestStatus` | Yes | **Yes** |
| `UserOrgChartGroup` | Yes | **Yes** |

When generating transfers, **reference existing roles/statuses by ID** — do not assume users migrate with configuration.

## User

End-user accounts (LDAP, mobile, notifications, delegation).

Hints cover: login, manager, 2FA, mobile device settings.

## UserAccess

Per company/object/type/role access rules.

Must be configured separately in each environment after transfer.

## Role

Workflow participant definition.

Flags include Requestor, Owner.

Referenced by `Workflow`, `WorkflowStep`, `WorkflowStepAction`.

## OrgChart

**Tables:** `UserOrgChartGroup`, `UserOrgChartCategory`

Organizational chart for approval routing.

`WorkflowStep.UserOrgChartGroupID` restricts step to users with matching org chart.

## Service Account

Not in DB or Object Transfer. GraphQL and Node.js object actions run as **user ID `0`**.

`Context.GraphQL.Token` is the bearer token for that service account, not the interactive user. `XeeloGraphQLClient` uses it on every `Select_` / `Mutate_`.

Grant **WRITE** in Admin (`UserAccess`) on **each object** the script mutates — including a different object targeted by `createType: CREATE`. After `/publish`, tell the user to check this before testing.

GraphQL access tokens have separate **read / write / delete** sets per object. `Delete_request` needs **delete**, not write. Query `access_rights` to see `canRead` / `canWrite` / `canDelete`. See [graphql.md](graphql.md#mutation-delete_request).

See [nodejs-esm.md](nodejs-esm.md) and [nodejs-graphql-patterns.md](../../recipes/nodejs-graphql-patterns.md).

## Agent guidance

1. Generate config (objects, workflows) via xeelo-skills
2. Process DB transfer on target site
3. **Manually** create/sync users and access in Admin or via separate tooling — including **WRITE for service account 0** when Node.js GraphQL mutates objects

See [`AGENT.md`](../../AGENT.md) — "What DB transfer includes / excludes".
