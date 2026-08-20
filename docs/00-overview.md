# Xeelo Overview

Xeelo is a metadata-driven **workflow and request-management platform** (SmarterMDM family). Each **Site** is a tenant with its own SQL database.

## Core concepts

| Term | Meaning |
|------|---------|
| **Object** | Configurable form definition (admin metadata) |
| **Request** | Runtime instance of an Object — user data flowing through workflow |
| **Workflow** | Approval/process definition (steps, actions, roles, statuses) |
| **Role** | Workflow participant (e.g. Requestor, Owner) |
| **Request Status** | Lifecycle state (Draft, Active, Completed, …) |
| **Company** | Top-level org grouping |
| **Object Type** | Category for objects (icon, color, order) |
| **Object Template (ObjectDefault)** | Default values, validation, lookup bindings, create-form access ([object-model.md](entities/object-model.md#create-form-access-objectdefaultaccess)) |
| **Update action (ObjectUpdateAction)** | User update on completed request → new version; field visible/editable via **ObjectUpdateAccess** ([update-actions.md](entities/update-actions.md)) |
| **Object action (ObjectAction)** | Server automation on Save / workflow; Node.js Last: [object-actions.md](entities/object-actions.md), [nodejs-esm.md](entities/nodejs-esm.md) |
| **GraphQL** | Per-site `Select_` / `Mutate_` from object codes; `lines` vs `linesFormatted`: [graphql.md](entities/graphql.md) |
| **Reference (ObjectLineSource)** | Číselník for combo/radio/multi — bind on **ObjectLine**; spec `spec/references.yaml` |
| **Lookup (ObjectLineLookup)** | Query map on **template line** — fills the field from another line (`sourceField`) |
| **Autonumber (ObjectLineAutoNumber)** | Site sequence (format + next); bind on **template line** — [object-model.md](entities/object-model.md#autonumber) |
| **Unique** | `ObjectLineUniqueID` level on a line — uniqueness among submitted requests — [object-model.md](entities/object-model.md#unique) |
| **Localization (LanguageTable)** | Translated labels for objects, tabs, sections, fields — [localization.md](entities/localization.md) |

## Configuration vs runtime

| Layer | Where | In DB transfer? |
|-------|-------|-----------------|
| Form layout, workflow, integrations | Admin metadata tables | Yes |
| Users, access assignments | `User`, `UserAccess` | **No** |
| Submitted request data | Request tables | **No** |

## Object form hierarchy

```
Object
└── ObjectLineTab (placement 0=left, 1=right)
    └── ObjectLineSection
        └── ObjectLine (field: type, slot, width)
            └── [optional] ObjectSub (sub-grid)
```

Template layer (required for usable object):

```
ObjectDefault (links Object + Workflow)
└── ObjectDefaultLine (per ObjectLine: validation, lookup, autonumber, calculations)
```

## Admin grouping

See [01-entity-hierarchy.md](01-entity-hierarchy.md) for portlet-grouped entity list.

## Further reading

- [transfer/object-transfer-format.md](transfer/object-transfer-format.md) — **generate** Object Transfer packages
- [transfer/db-transfer-format.md](transfer/db-transfer-format.md) — download/parse DB transfer → env baseline
- [transfer/spec-format.md](transfer/spec-format.md) — agent input language (v2)
- [entities/graphql.md](entities/graphql.md) — `Select_` / `Mutate_`, `lines` vs `linesFormatted`
- [entities/object-line-types.md](entities/object-line-types.md) — 20 ObjectLine types, template capabilities, client calc
- [entities/xeelo-grammar.md](entities/xeelo-grammar.md) — extended validation (`v#`), Client-Math/String, UserInfo/DeviceInfo
- [entities/localization.md](entities/localization.md) — `LanguageTable`, `spec/language-table.yaml`
- [../AGENT.md](../AGENT.md) — project loop (download → env → change-loop OT)
- [projects.md](projects.md) — nested private git for `projects/`
