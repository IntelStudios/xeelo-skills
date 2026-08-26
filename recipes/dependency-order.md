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
| 9s | `ObjectService` | — |
| 9a | `ObjectSub` | — |
| 9b | `ObjectSubLineTab` | — |
| 9c | `ObjectSubLineSection` | ObjectSubLineTab |
| 9d | `ObjectSubLine` | ObjectSub, ObjectSubLineSection |
| 9e | `ObjectSubLineOnGrid` | ObjectSubLine |
| 10 | `ObjectLine` | Object, ObjectLineSection (`ObjectSubID` if type 5 → ObjectSub) |
| 10a | `Notification` | — (site catalog; emit before Workflow FKs) |
| 10b | `NotificationCondition` | Notification, ObjectLine |
| 10c | `NotificationAttachment` | Notification, ObjectLine |
| 11 | `Workflow` | Role, RequestStatus, Notification |
| 12 | `WorkflowStep` | Workflow, Role, RequestStatus |
| 13 | `WorkflowStepAccess` | WorkflowStep, ObjectLine (`ObjectSubLineID` optional) |
| 14 | `WorkflowStepAction` | WorkflowStep, Role, RequestStatus, WorkflowStepActionStyle, Notification |
| 14a | `WorkflowStepNotification` | WorkflowStep, Notification |
| 15 | `ObjectDefault` | Object, Workflow |
| 16 | `ObjectDefaultAccess` | ObjectDefault, ObjectLine (`ObjectSubLineID` optional) |
| 16a | `ObjectSubDefault` | ObjectSub |
| 16b | `ObjectSubDefaultLine` | ObjectSubDefault, ObjectSubLine, ObjectLineAutoNumber?, ObjectService? |
| 17 | `ObjectDefaultLine` | ObjectDefault, ObjectLine, ObjectLineLookup?, ObjectLineAutoNumber?, ObjectService?, ObjectSubDefault? |
| 18 | `ObjectUpdateAction` | Object |
| 19 | `ObjectUpdateAccess` | ObjectUpdateAction, ObjectLine (`ObjectSubLineID` optional) |
| 19a | `ObjectMessage` | Object |
| 19b | `ObjectMessageCondition` | ObjectMessage, ObjectLine |
| 19c | `ObjectUpdateMessage` | ObjectUpdateAction, ObjectMessage |
| 20 | `ObjectAction` | Object |
| 21 | `ObjectActionParam` | ObjectAction |
| 22 | `ObjectActionCondition` | ObjectAction, ObjectLine |
| 23 | `WorkflowStepObjectAction` | WorkflowStep, ObjectAction |
| 24 | `Periodic` | Object |
| 25 | `PeriodicCondition` | Periodic, ObjectLine |
| 26 | `PeriodicAction` | Periodic |
| 27 | `PeriodicActionParam` | PeriodicAction |
| 28 | `PeriodicActionCondition` | PeriodicAction, ObjectLine |
| 29 | `Scheduler` | — |
| 30 | `SchedulerLine` | Scheduler |
| 31 | `SchedulerLineParam` | SchedulerLine (`PeriodicID` value) |
| 32 | `LanguageTable` | Parent entity PK in `RowID` (Object, ObjectLine, Periodic, …) |
| 33 | `TableComments` | Parent entity PK in `TableRowID` (Object, ObjectLine, Periodic, …) |

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
