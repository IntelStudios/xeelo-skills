---
name: ui-test-workflow-action
description: >-
  Run a workflow action from the open request (header Workflow modal, action
  tiles). Use from /ui-test after fill+save. Not the inbox on-grid wheel.
disable-model-invocation: true
---

# Workflow action (request form)

Need an open request ([../fill-save/SKILL.md](../fill-save/SKILL.md)). Inbox mass / option-wheel actions are [../inbox/SKILL.md](../inbox/SKILL.md).

## Steps

1. In the **request header**, click **Workflow** (`SmartMDMUI.Workflow`).
2. A modal lists **action tiles** (names from the workflow — match the name the user gave, or the only enabled tile).
3. Click the tile. If **Select user** appears, pick the user the test account may assign (ask if unclear) and **OK**.
4. Optional **Comments** — skip unless the user asked.
5. Wait until the modal closes and the request refreshes.

If the modal warns that mandatory fields are empty, close it, finish [fill-save](../fill-save/SKILL.md), then retry. Do not force a special/admin override action unless the user named it.

**Success:** chosen action is gone or the request shows a new role/status (header, chips, or info). Say what you see.

**Fail:** no Workflow button (no rights / completed / no actions), all tiles disabled, or an error after click — stop and report.
