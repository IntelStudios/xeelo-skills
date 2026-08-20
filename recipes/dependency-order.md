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
| 9 | `ObjectLineAutoNumber` | — |
| 10 | `ObjectLine` | Object, ObjectLineSection |
| 11 | `Workflow` | Role, RequestStatus |
| 12 | `WorkflowStep` | Workflow, Role, RequestStatus |
| 13 | `WorkflowStepAccess` | WorkflowStep, ObjectLine |
| 14 | `WorkflowStepAction` | WorkflowStep, Role, RequestStatus, WorkflowStepActionStyle |
| 15 | `ObjectDefault` | Object, Workflow |
| 16 | `ObjectDefaultAccess` | ObjectDefault, ObjectLine |
| 17 | `ObjectDefaultLine` | ObjectDefault, ObjectLine, ObjectLineLookup?, ObjectLineAutoNumber? |
| 18 | `ObjectUpdateAction` | Object |
| 19 | `ObjectUpdateAccess` | ObjectUpdateAction, ObjectLine |
| 19a | `ObjectMessage` | Object |
| 19b | `ObjectMessageCondition` | ObjectMessage, ObjectLine |
| 19c | `ObjectUpdateMessage` | ObjectUpdateAction, ObjectMessage |
| 20 | `ObjectAction` | Object |
| 21 | `ObjectActionParam` | ObjectAction |
| 22 | `ObjectActionCondition` | ObjectAction, ObjectLine |
| 23 | `WorkflowStepObjectAction` | WorkflowStep, ObjectAction |
| 24 | `LanguageTable` | Parent entity PK in `RowID` (Object, ObjectLine, …) |

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
