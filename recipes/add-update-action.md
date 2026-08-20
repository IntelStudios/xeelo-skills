# Add Update Action

Add an **ObjectUpdateAction** so users can create a **new request version** after the current one is **Completed**.

Entity reference: [docs/entities/update-actions.md](../docs/entities/update-actions.md)

## Preconditions

- Object exists with layout + **ObjectDefault** (template) and workflow including a **Completed** status step
- Target site has roles/statuses referenced by the template workflow
- For user visibility: configure **ObjectUpdateActionUserList** in Admin (not in Object Transfer)

## Ask which workflow

**Always ask** which workflow the **new request version** should use (`ObjectUpdateAction.WorkflowID`) before writing `spec/update-actions.yaml`. Skip only if the user already chose in the same request. Playbook: [AGENT.md § Ask which workflow](../AGENT.md#ask-which-workflow).

First option is **Recommended** — the default template’s workflow (`ObjectDefault` with `isDefault: true`, or the only template). **Omit** `updateActions[].workflow` so `WorkflowID` is NULL; runtime falls back to the template. Label the option **object — workflow name — id** from `spec/workflow.yaml` + `ids.explicit.workflowId`.

Then offer other existing workflows from site `env/` (same listing as a new object). If they pick one, set `updateActions[].workflow` to that shared Orig. ID. Third option: **new workflow** for this update version.

## Admin UI path

Object Detail → **Update Actions**:

1. **Create action** — name, order, template scope (all or one ObjectDefault), **Workflow** for the new version (ask first; default = template WF), quick flag, tab focus
2. **Conditions** — when the action appears on completed requests (`spRequestUpdateActionList`)
3. **Access** — per-line editable/visible flags during EditableUpdate
4. **Users** — allow list (`ObjectUpdateActionUserList`)
5. **Messages** — optional object messages on the update form ([object-messages.md](../docs/entities/object-messages.md))

## Spec / Object Transfer path

Optional fragments `spec/update-actions.yaml` and `spec/object-messages.yaml` (see [spec-format.md](../docs/transfer/spec-format.md)):

```yaml
objectMessages:
  - key: warning_msg
    name: Confirm change
    style: warning
    order: 10
    html: |
      <p>This change will update related records.</p>
updateActions:
  - key: amend
    name: Amend record
    order: 10
    access:
      - field: FIELD_CODE
        editable: true
        visible: true
    messages:
      - key: warning_msg
        visible: true
    # omit workflow: → template ObjectDefault workflow (default after asking)
```

Refresh default for update access is **visible yes, editable no** — list every field that must be editable (or `visible: false` to hide). Same dual-list as template create access (`templates[].access`) and `workflow.steps[].access`; see [object-model.md](../docs/entities/object-model.md#create-form-access-objectdefaultaccess).

Include in `xeelo-spec.yaml`:

```yaml
includes:
  - spec/object.yaml
  - spec/workflow.yaml
  - spec/object-messages.yaml
  - spec/update-actions.yaml
  - spec/ids.yaml
```

Populate `ids.explicit.updateActions`, `objectUpdateAccess`, etc. from Admin export or extract:

```bash
python scripts/extract-object-transfer-to-spec.py \
  path/to/object-transfer.xml \
  --object-id <id> \
  -o projects/<project>/env/objects/<slug>
```

Generate OT via change loop:

```bash
python scripts/generate-change-loop.py projects/<project>/changes/<slug>
```

**Transfer scope:** `ObjectUpdateAction`, `ObjectUpdateAccess`, `ObjectUpdateActionCondition`, `ObjectMessage`, `ObjectUpdateMessage`. **Not** `ObjectUpdateActionUserList` (configure users in Admin after deploy).

## Checklist

- [ ] Template workflow can reach **Completed**
- [ ] Update action defined with order and name
- [ ] Line access set (defaults: visible yes, editable no — list `editable: true` for fields to change)
- [ ] Conditions if action should not always appear
- [ ] User allow list in Admin
- [ ] Object message on the update form if the user must confirm (Warning = Cancel/Continue; Error blocks Continue)
- [ ] Asked which workflow (default = default ObjectDefault WF; omit `workflow:` unless they picked another or a new WF)
- [ ] Spec `ids.explicit` populated for Orig. ID import
- [ ] OT package includes ObjectUpdateAction subtree

## Troubleshooting

| Symptom | Check |
|---------|--------|
| No update buttons on request | Request must be **Completed** |
| Action missing for some users | `ObjectUpdateActionUserList` / User Access Detail |
| Action missing for some requests | Conditions failed (`spRequestUpdateActionList`) |
| Wrong workflow on new version | `ObjectUpdateAction.WorkflowID` vs template fallback |
| Wrong fields editable | `ObjectUpdateAccess` for that action |

## Planned: WorkflowStepAction M:N

Target model: junction table linking **WorkflowStepAction** ↔ **ObjectUpdateAction** (not in current platform schema). Until then, update actions are offered on all completed requests for the object (filtered by conditions + users).

## Sample

[`projects/cars/`](../projects/cars/) — `ObjectUpdateAction` id 5118 in Object Transfer extract.
