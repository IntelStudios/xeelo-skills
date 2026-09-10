---
name: ui-test-inbox
description: >-
  Find a request on the User UI inbox/grid, check onGrid values, optional
  on-grid workflow wheel. Use from /ui-test after login or save.
disable-model-invocation: true
---

# Inbox

Need login ([../login/SKILL.md](../login/SKILL.md)). Grid is the object inbox (Items/Tasks), not Admin.

Typical paths after login: object tree → object → grid. Request form URL is under `/xeelo/tasks/request/{id}`; the object grid is under `/xeelo/tasks/grid/{id}`. Prefer clicking the tree over typing IDs.

onGrid columns and modules: [ongrid.md](../../docs/entities/ongrid.md).

## Find a row

Identify the request by **title**, autonumber, or text the user gave. Use grid search/filter if the list is long. Open the row only if the user wants the form; otherwise read the card/table in place.

**Success:** the row is visible. If the user named an onGrid field, say the visible cell text.

## On-grid workflow (option wheel)

Only when the user asked, and spec has `actions[].isOnGrid: true` ([workflow.md](../../docs/entities/workflow.md)).

That is the inbox row menu (option wheel / mass action), **not** the request-header Workflow button. After choosing the action, the same workflow modal as [workflow-action](../workflow-action/SKILL.md) may open (tiles, optional user, comments).

If the wheel has no workflow action, stop — the action may be form-only.
