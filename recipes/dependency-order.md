# Global Dependency Order

Insert / generate tables in this order to satisfy foreign keys.

## Create object (minimal)

| Order | Table | Depends on |
|-------|-------|------------|
| 1 | `Company` | — |
| 2 | `ObjectType` | — |
| 3 | `Role`, `RequestStatus` | usually existing |
| 4 | `Object` | Company, ObjectType |
| 5 | `ObjectLineTab` | — |
| 6 | `ObjectLineSection` | ObjectLineTab |
| 7 | `ObjectLineLookup` | — |
| 8 | `ObjectLineLookupValue` | ObjectLineLookup |
| 9 | `ObjectLine` | Object, ObjectLineSection |
| 10 | `Workflow` | Role, RequestStatus |
| 11 | `WorkflowStep` | Workflow, Role, RequestStatus |
| 12 | `WorkflowStepAccess` | WorkflowStep, ObjectLine |
| 13 | `WorkflowStepAction` | WorkflowStep, Role, RequestStatus, WorkflowStepActionStyle |
| 14 | `ObjectDefault` | Object, Workflow |
| 15 | `ObjectDefaultLine` | ObjectDefault, ObjectLine, ObjectLineLookup? |
| 16 | `ObjectAction` | Object |
| 17 | `ObjectActionParam` | ObjectAction |
| 18 | `ObjectActionCondition` | ObjectAction, ObjectLine |
| 19 | `WorkflowStepObjectAction` | WorkflowStep, ObjectAction |

## Full transfer table list

Alphabetical list with types: [`data/transfer-tables.json`](../data/transfer-tables.json)

Processor source: `spAdminDbSetupXMLProcessBatch.sql` — deletes and re-inserts in table list order.

## Type legend

| Type | Meaning |
|------|---------|
| U | Unit — standalone or parent |
| D | Detail — child rows |
| X | Cross-reference / value data |

## Not in transfer

These are **never** emitted for DB transfer:

- `User`, `UserAccess`, `UserDelegation`
- All `Request*` runtime data tables
- `DbSetupXML`, `ObjectSetupXML` (transfer staging)
