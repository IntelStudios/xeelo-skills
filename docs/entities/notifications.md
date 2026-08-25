# Notifications

Email templates sent on workflow events, ObjectAction, or Periodic. A `Notification` row is a **site catalog** (no `ObjectID`). Object Transfer pulls it in as a child of `Workflow`, `WorkflowStepAction`, `WorkflowStepNotification`, `ObjectAction`, or `PeriodicAction`.

Schemas: [`Notification.json`](../data/schemas/Notification.json), [`NotificationCondition.json`](../data/schemas/NotificationCondition.json), [`NotificationAttachment.json`](../data/schemas/NotificationAttachment.json), [`WorkflowStepNotification.json`](../data/schemas/WorkflowStepNotification.json) · types: [`NotificationType.json`](../data/enums/NotificationType.json)

Spec fragment: [`spec/notifications.yaml`](../transfer/spec-format.md#notifications-specnotificationsyaml)

## Do not confuse

| Entity | Purpose |
|--------|---------|
| **Notification** | Email template (subject + HTML body + recipients). In Object Transfer. |
| **UserNotification** | Per-user email preference (company/object/type). **Not** in DB/Object Transfer. |
| **In-app / push** | Runtime from `NotificationData` after send. Not the template. |
| **ObjectMessage** | HTML **modal** on the form (Cancel / Continue). [object-messages.md](object-messages.md) |
| **ConfirmMethod Push** | Workflow button confirmation in MobileApp. Not email. |

## Types (seed)

| ID | Spec `type` | Name | When |
|----|-------------|------|------|
| 1 | `single` | Single request | One request (`spNotificationDataInsert`) |
| 2 | `summary` | Request summary | Batch (`spNotificationDataInsertSummary` + `{RequestGrid,…}`) |

`NotificationType` is **not** in Object Transfer (site seed).

## Runtime

```text
event (SaveNew / WorkflowAction / …)
  → spNotificationDataInsert(RequestID, event, optional NotificationID)
      → resolve template(s)  # this proc: NotificationTypeID = 1 only
      → conditions (AND across fields, OR on the same field)
      → spNotificationCalculation + NotificationTempCalc (runtime; not spec v1)
      → recipients
      → fnRequestFormat(subject, style=plain)
      → fnRequestFormat(body, style=HTML)  # wraps in <html>+CSS
      → optional offline-action tokens
      → NotificationData + email job + in-app
```

After a workflow event (not `PeriodicAction` / `Comment` / `ObjectAction`), the request is marked `RequestIsNotified = 1`, so step-junction templates do not fire again until that flag is cleared. `Comment` sets `RequestCommentIsNotified` instead.

Event string → where the template ID comes from:

| Event | Source |
|-------|--------|
| `WorkflowAction` | `WorkflowStepAction.NotificationID` **and** `WorkflowStepNotification` on the **target** step (current role + status; `RequestIsNotified = 0`; optional `RequestTypeID` filter) |
| `SaveNew` | `Workflow.NotificationID` (on create) + step notifications (same `RequestIsNotified` / `RequestTypeID` filter) |
| `ExportFail` | `Workflow.ExportFailNotificationID` **and** step notifications (`RequestIsNotified` / `RequestTypeID`) |
| `ExportFailNoUpdate` | `Workflow.ExportFailNotificationID` only (no step junctions) |
| `WorkflowRecall` | `Workflow.RecallNotificationID` **and** step notifications |
| `WorkflowFail` | `Workflow.WorkflowFailNotificationID` **and** step notifications |
| `WorkflowUpdate` | step notifications only |
| `ObjectAction` | param `NotificationID1` (type `spNotificationDataInsert` / `…Last`) |
| `PeriodicAction` | param `NotificationID1` (single) or `NotificationID2` (summary) |
| `Comment` | explicit ID; offline-action tokens are **not** expanded |

ObjectAction types: **Notification single request** (`spNotificationDataInsert`) and **(Last)** (`spNotificationDataInsertLast`). Periodic: the same single type, plus **Notification request summary** (`spNotificationDataInsertSummary`).

## Recipients

Bits on `Notification`. Spec `sendTo:` (omit / false = off):

| Spec | Column | Meaning |
|------|--------|---------|
| `requestor` | `NotificationEmailRequestor` | Requestor (**To**) |
| `requestorManager` | `NotificationEmailRequestorManager` | Requestor’s manager (**Cc**, only with `requestor`) |
| `owner` | `NotificationEmailOwner` | Owners (**To**) |
| `watch` | `NotificationEmailWatch` | Watchers (**To**) |
| `role` | `NotificationEmailRole` | Assigned users in the **new** role (**To**). In-progress: task list; completed/canceled: `RequestUserList` |
| `roleManager` | `NotificationEmailRoleManager` | Managers of those assigned users (**Cc**, only with `role`) |
| `currentUser` | `NotificationEmailUser` | User who triggered the event (`LastWorkflowUserID`) (**To**) |

`extra.to` / `cc` / `bcc` and `fromEmail` may be a literal address, `{idNNNN}` (**raw** slot via the line id — combo **bind**, not the numberedník name), or `{Variable,code}`. Extra **To** splits on comma, semicolon, or space; each token must contain `@` and `.`. Empty `fromEmail` uses the site SMTP From. If application setting **EmailFromDomainDifference** is on and the From domain differs from the site From, the site address stays **From** and the template address becomes **Reply-To**.

`UserNotification` (via the per-user view) can suppress mail (`IsEmailSend = 0`) unless the site ignores them for summary. Extra addresses use `UserID = 0` and always send. Suspended users are forced off. A populated manager **Cc** forces `IsEmailSend = 1` for that row.

## Data model

```text
Notification
  ├── NotificationTypeID (seed 1/2)
  ├── subject + HTML format
  ├── recipient bits + extra emails
  ├──< NotificationCondition   (same type catalog as update-action)
  ├──< NotificationAttachment  (ObjectLine file; default zip)
  ├──< NotificationPrintout    (not in spec v1)
  └──< NotificationCalculation / NotificationTempCalc  (not in spec v1)

Workflow.NotificationID / ExportFail / Recall / Fail
WorkflowStepAction.NotificationID
WorkflowStep ──< WorkflowStepNotification ──> Notification
ObjectActionParam NotificationID1
PeriodicActionParam NotificationID1 | NotificationID2
```

Conditions: `fnRequestLineDataCondition` per row. **OR** among conditions on the **same** `ObjectLineID`; **AND** across different fields. Any remaining failed row blocks the send. No conditions → always send once resolved.

`WorkflowStepNotification.RequestTypeID` (nullable): runtime keeps the junction only when it matches the request’s Create/Update type (`isnull(RequestTypeID, requestType) = requestType`). **Null = both.** Spec/generate omit the column (new OT rows stay null).

Attachments: ObjectLine (type attachment). `compressed` defaults **true**. Optional zip name: `compressedFileName` (plain placeholders).

## Admin UI

**Notification** portlet: name, type, recipients, extra/from, subject, HTML body (intellisense), conditions, attachments, printouts, calculations.

Bind:

- Workflow header — create / export-fail / recall / fail
- Workflow step action — that transition button
- Workflow step → notifications list (`WorkflowStepNotification`)
- Object Action / Periodic Action params — pick a single or summary template

## Placeholders

Subject and body go through `fnRequestFormat`. **Subject** = plain text (`style` 2). **Body** = HTML (`style` 1) and is wrapped in a full HTML document with table CSS (HTML style only).

Tokens are `{Name}` or `{Name,arg1,arg2,…}`. Admin’s `NotificationFormat` hint is **incomplete**. Generate/extract **do not rewrite** tokens. Spec must use **numeric `ObjectLineID`** in `{idXXXX}` — `{idAMOUNT}` is not resolved.

### Request lines (plain and HTML)

Same `ObjectLineID` as GraphQL `lines` / `linesFormatted`. `{idXXXX}` is the **formatted** value; `{idXXXXv}` is the **raw slot** (stored bind / valueData). `{idXXXXp}` is formatted from the previous completed version.

| Token | Meaning |
|-------|---------|
| `{idXXXX}` | Formatted line value |
| `{idXXXXp}` | Previous value, formatted (update) |
| `{idXXXXv}` | Raw slot (combo **bind**, not the numberedník name) |

| Line type | `{idXXXX}` | `{idXXXXv}` |
|-----------|------------|-------------|
| Combobox / radio / multi | Reference **name** (label) | Stored **bind** |
| Memo (type 11) | Memo **HTML** | Do not use — not the memo body |
| Text / number / date | Display-formatted | Stored slot |

Put memo HTML in the email body with `{idNNNN}` (no `v`). In HTML style the substitution is **not** escaped, so a memo that already contains markup stays markup. Grammar suffixes `idNr` / `idNm` are **not** notification tokens (they expand to empty).

Admin Intellisense on Notification / Printout offers `id`, `idp`, and `idv`. `{idAMOUNT}` is still not resolved — the number must be the site `ObjectLineID`.

### Scalars (subject and body)

Dates: `{Today}` `{TodayTime}` `{TodaySerial}`

Request: `{RequestID}` `{RequestLink}` `{RequestType}` `{RequestPriority}` `{RequestStatus}` `{RequestStatusID}` `{RoleName}` `{RoleID}` `{ObjectName}` `{CompanyName}` `{ObjectTypeName}` `{ObjectDefaultName}` `{ObjectDefaultID}` `{ObjectUpdateActionID}` `{ObjectUpdateActionName}` `{RequestorID}` `{RequestorName}` `{RequestorLogin}` `{RequestorEmail}` `{RequestorLanguage}` `{RequestorAssigned}` `{NotAssigned}` `{CreatedDate}` `{CreatedByID}` `{CreatedByName}` `{ModifiedDate}` `{ModifiedByID}` `{ModifiedByName}` `{CompletedDate}` `{CompletedByName}` `{LastActionDate}` `{LastActionName}` `{LastActionID}` `{ActionDuration}` `{LastComment}` `{LastRoleName}` `{LastRequestStatus}` `{LastWorkflowUserID}` `{LastWorkflowUserName}` `{PrevUserName}` `{NextUserName}` `{AssignedUserName}` `{AssignedUserID}` `{OwnerUserName}` `{OwnerUserID}` `{WatcherUserName}` `{WatcherUserID}`

Parametric: `{Variable,code}` `{TempCalc,id}`

`{RequestPriority}` is the **priority ID**, not a name. `{NextUserName}` is the assigned-user list (same as `{AssignedUserName}`).

### HTML-only (body)

Width is percent. Optional extra args are ObjectLine IDs.

Tables: `{RequestDetail,w,…}` / `{RequestDetails,w,…}` · `{RequestDetailFilter,w,…}` / `{RequestDetailsFilter,w,…}` (create = filled lines only; update = changed only) · `{RequestComment,w}` / `{RequestComments,w}` · `{RequestCommentsNew,w}` / `{RequestCommentNew,w}` · `{RequestCommentsPrev,w}` / `{RequestCommentPrev,w}` · `{RequestWorkflow,w}` · `{RequestSubGrid,w,lineId,subLineIds…}` · `{RequestSubGridNoHeader,…}` · `{RequestSubGridTotal,…}` · `{RelationGrid,w,objectId,lineIds…}`

Other: `{BarCode,lineId,style[,width[,height]]}` (defaults width 2, height 60) · `{QRCode,lineId}` · `{ProgressBar,height,isLabel,valueOrId,colorOrId}` (`isLabel` is 0/1) · `{Condition,expr,true,false}` · `{Condition2,id,expr}` `{Condition2Else,id}` `{Condition2End,id}`

`BarCode` / `QRCode` / `Condition` / `Condition2` in HTML style emit a placeholder plus **jQuery in the mail body** (barcode/QR scripts from the site `ServerAddress`; `Condition` uses `eval`). They are not pure server-side HTML.

### After format, single email only (not `Comment`)

`{RequestOfflineActions}` · `{RequestOfflineActionsWithRequestLink}` · `{RequestOfflineActionsHash,actionId}`

### Summary type only

`{RequestGrid,width,lineId,…}` — table of requests in the batch. Runtime: 2nd arg = width, further args = ObjectLine IDs (Admin Intellisense mentions Object ID; summary SQL does not use a separate object id). `{Variable,code}` is also expanded in summary.

### Not expanded in notification body

`{ReportResult,…}` is Printout-only.

These exist on the placeholder helper but **notification format does not call them** (left as literal text): `{TodayYear}` `{TodayMonth}` `{RequestorInfo01}`–`{RequestorInfo09}` `{RequestState}` `{TimeInCurrentStep}` `{CompletedByID}` `{ApproveStepWorkflowUserID}` `{ApproveStepWorkflowUserName}` `{SubLineNext}`. `{RequestTag}` and `{CompletedBy}` are listed for format but have no placeholder branch — also left as text.

Subject/body are **not** `LanguageTable`-localized in User precompile (cache stores the raw subject/format).

## Transfer / spec

| In Object Transfer | Not in transfer / not in spec v1 |
|--------------------|----------------------------------|
| `Notification`, `NotificationCondition`, `NotificationAttachment`, `WorkflowStepNotification` | `NotificationType`, `NotificationConditionType`; `NotificationPrintout`, `NotificationCalculation`, `NotificationTempCalc`; `UserNotification` |

Emit rows from `spec/notifications.yaml`. Bind with keys:

- `workflow.notification` / `exportFailNotification` / `recallNotification` / `failNotification`
- `workflow.steps[].actions[].notification`
- `workflow.steps[].notifications: [key]` (does not set `RequestTypeID`; null = Create and Update)
- ObjectAction / PeriodicAction `params.NotificationID1: { notification: key }` (`NotificationID2` for summary)

A template in `notifications:` must be bound to at least one of those (OT has no `Object → Notification` edge). Linking a key that is only in `ids.explicit.notifications` (no fragment row) assumes the site already has that Orig. ID.

`workflow.reuse: true` does not upsert Workflow / step / action rows, so header and action FKs on a shared process are not changed. Step junction rows can still be emitted. Prefer ObjectAction / Periodic params to attach a new template to a reused workflow.

## Recipe

[`add-notification.md`](../../recipes/add-notification.md)
