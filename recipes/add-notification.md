# Add Notification

Add an **email template** (`Notification`) and bind it from a workflow, ObjectAction, or Periodic. Entity reference: [docs/entities/notifications.md](../docs/entities/notifications.md). Spec: [spec-format.md](../docs/transfer/spec-format.md#notifications-specnotificationsyaml).

A template is a **site catalog** (no `ObjectID`). Object Transfer includes it only as a child of Workflow / WorkflowStepAction / WorkflowStepNotification / ObjectAction / PeriodicAction. An unbound `notifications[].key` is a generate error.

## Preconditions

- Object has a workflow (new or reused) if you bind from `workflow.*` or a step action
- Attachment fields already exist when listing `attachments[]`
- `{idXXXX}` in `subject` / `format` uses numeric **ObjectLineID**, not the field code
- Memo HTML in the body is `{idNNNN}` (formatted). `{idNNNNv}` is the raw slot (combo bind); do not use it for memo

## Ask

Where the mail should fire:

1. **Submit / workflow button** — `workflow.steps[].actions[].notification` (`WorkflowAction`)
2. **On create** — `workflow.notification` (`SaveNew`)
3. **On a step** (every arrival) — `workflow.steps[].notifications: [key]`
4. **ObjectAction** — type `spNotificationDataInsert` or `spNotificationDataInsertLast`, param `NotificationID1: { notification: key }`
5. **Periodic** — `spNotificationDataInsert` (single, `NotificationID1`) or `spNotificationDataInsertSummary` (summary, `NotificationID2`)

Default for “email when they Submit” = option 1 on the Submit action.

`workflow.reuse: true` does not change header or action FKs on the shared process. Prefer ObjectAction / Periodic params, or `steps[].notifications` (junction still emits).

## Admin UI path

1. **Notification** — name, type (single / summary), recipients, extra/from, subject, HTML body, conditions, attachments
2. Bind: Workflow header, step action, step → notifications list, or Object/Periodic Action params

## Spec / Object Transfer path

Fragment `spec/notifications.yaml`:

```yaml
notifications:
  - key: assigned
    name: Assigned to role
    type: single
    subject: "{ObjectName} {RequestID}"
    format: |
      <p>Request {RequestID} ({ObjectName})</p>
      <p>{RequestDetails,100}</p>
    sendTo:
      role: true
      requestor: true
```

Workflow (Submit):

```yaml
workflow:
  mode: full
  steps:
    - name: Draft
      role: requestor
      status: draft
      actions:
        - name: Submit
          role: owner
          status: active
          notification: assigned
    - name: Active
      role: owner
      status: active
```

ObjectAction:

```yaml
objectActions:
  - key: notify_assigned
    name: Notify assigned
    typeCode: spNotificationDataInsert
    order: 10
    workflowSteps: [Draft]
    params:
      NotificationID1: { notification: assigned }
      ApplicableEventType: "SaveNew,WorkflowAction"
```

Periodic (single vs summary):

```yaml
periodics:
  - key: daily_summary
    name: Daily summary
    requestType: in_progress
    cron: "0 0 7 ? * * *"
    actions:
      - key: send_summary
        name: Send summary
        typeCode: spNotificationDataInsertSummary
        order: 10
        params:
          NotificationID2: { notification: assigned }
```

Use `spNotificationDataInsert` + `NotificationID1` for one request per tick. Summary templates should set `type: summary` and use `{RequestGrid,…}` in the body.

Include in `xeelo-spec.yaml`:

```yaml
includes:
  - spec/object.yaml
  - spec/workflow.yaml
  - spec/notifications.yaml
  - spec/ids.yaml
```

Generate:

```bash
python scripts/generate-change-loop.py projects/<project>/changes/<slug>
```

**Transfer scope:** `Notification`, `NotificationCondition`, `NotificationAttachment`, `WorkflowStepNotification`. **Not** `NotificationType`, `NotificationPrintout`, `NotificationCalculation`, `UserNotification`.

## Checklist

- [ ] Template is bound (workflow header / action / step list / ObjectAction / Periodic)
- [ ] Recipients: `sendTo` bits and/or `extra.to` (`requestorManager` / `roleManager` are **Cc**; extra may be `{idNNNN}` raw or `{Variable,code}`)
- [ ] `{idXXXX}` uses site `ObjectLineID` after extract (not `{idAMOUNT}`)
- [ ] Memo HTML in `format` is `{idNNNN}` without `v` (combo bind is `{idNNNNv}`)
- [ ] Single vs summary type matches the executable (`spNotificationDataInsert` vs `…Summary`); summary body uses `{RequestGrid,…}` not `{RequestList}`
- [ ] Reused workflow: do not expect header/action FK upserts
- [ ] Conditions use the same slugs as update actions (`equals_text`, …); OR on the same field, AND across fields
