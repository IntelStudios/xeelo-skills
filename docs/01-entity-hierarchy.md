# Entity Hierarchy

Entities grouped as in Xeelo Admin site home (portlets).

```mermaid
flowchart TB
  subgraph org [Organization]
    Company
    ObjectType
  end
  subgraph objects [Objects]
    Object
    Object --> ObjectLineTab
    ObjectLineTab --> ObjectLineSection
    ObjectLineSection --> ObjectLine
    ObjectLine --> ObjectSub
    Object --> ObjectDefault
    ObjectDefault --> ObjectDefaultLine
    Object --> ObjectUpdateAction
    Object --> ObjectAction
    ObjectAction --> ObjectActionParam
    ObjectAction --> ObjectActionCondition
    ObjectLineLookup --> ObjectLineLookupValue
    ObjectDefaultLine --> ObjectLineLookup
  end
  subgraph wf [Workflows]
    Role
    RequestStatus
    Workflow
    Workflow --> WorkflowStep
    WorkflowStep --> WorkflowStepAction
    WorkflowStep --> WorkflowStepAccess
    WorkflowStep --> WorkflowStepObjectAction
    WorkflowStepObjectAction --> ObjectAction
    ObjectDefault --> Workflow
  end
  Company --> Object
  ObjectType --> Object
  Role --> WorkflowStep
  RequestStatus --> WorkflowStep
```

## Portlet map

### Companies & Types
- **Company** — org unit; `Object.CompanyID`
- **ObjectType** — categorization; `Object.ObjectTypeID`

### Objects
- **Object** — form definition
- **ObjectLineTab / Section / Line** — layout and fields
- **Subgrid (ObjectSub)** — embedded table on a line
- **ObjectDefault / ObjectDefaultLine** — template (defaults, validation, lookup)
- **Lookup / Reference / Autonumber** — field data sources
- **Update action (ObjectUpdateAction)** — post-completion user update → new request version
- **Object action (ObjectAction)** — server automation on save/workflow (`WorkflowStepObjectAction`)
- **Periodic** — scheduled automation
- **Calendar** — work calendars

### Workflows
- **Workflow** — process header (initial role/status, fail/recall handlers)
- **WorkflowStep** — step = role + status (+ optional org chart)
- **WorkflowStepAction** — transition buttons
- **WorkflowStepAccess** — which object lines are visible/editable on a step
- **WorkflowStepObjectAction** — which ObjectActions run at this step
- **Role**, **RequestStatus** — reference data (usually pre-existing)

### Integrations & outputs
- **Export / Import** — data pipelines
- **Notification / Printout / Report** — outputs
- **Scheduler, Object Service, Webhook** — automation

### Users (config UI, limited transfer)
- **User, UserAccess, Delegation, OrgChart** — **users not in DB transfer**

### Application Setup
- **Database Transfer** — full config XML/ZIP
- **Object Transfer** — selective object subtree

## DB transfer scope

110 tables — full list in [`data/transfer-tables.json`](../data/transfer-tables.json).

Priority tables for **create object** recipe:

`Company`, `ObjectType`, `Object`, `ObjectLineTab`, `ObjectLineSection`, `ObjectLine`, `ObjectLineLookup`, `ObjectLineLookupValue`, `Workflow`, `WorkflowStep`, `WorkflowStepAction`, `ObjectDefault`, `ObjectDefaultLine`, `ObjectAction`, `ObjectActionParam`, `ObjectActionCondition`, `WorkflowStepObjectAction`

## Entity docs

Detailed semantics from admin hints:

| Doc | Entities |
|-----|----------|
| [entities/object-model.md](entities/object-model.md) | Object, lines, templates, lookups |
| [entities/object-line-types.md](entities/object-line-types.md) | ObjectLine types 1–20, extras, template capabilities |
| [entities/xeelo-grammar.md](entities/xeelo-grammar.md) | Extended validation + Client-Math/String expressions |
| [entities/update-actions.md](entities/update-actions.md) | ObjectUpdateAction, access, conditions |
| [entities/object-actions.md](entities/object-actions.md) | ObjectAction, params, conditions, Run Node.js |
| [entities/nodejs-esm.md](entities/nodejs-esm.md) | ESM `CustomJS`, `Context`, no refresh on current request |
| [entities/graphql.md](entities/graphql.md) | `Select_` / `Mutate_` names, query args, `createType`, `lines` vs `linesFormatted` |
| [entities/workflow.md](entities/workflow.md) | Workflow, steps, actions |
| [entities/integrations.md](entities/integrations.md) | Export, import, periodic, scheduler |
| [entities/outputs.md](entities/outputs.md) | Notification, printout, report |
| [entities/users-and-access.md](entities/users-and-access.md) | Users vs transfer scope |
