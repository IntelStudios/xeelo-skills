---
name: ui-test-create-request
description: >-
  Create a request in Xeelo User UI (inbox Create / object picker / template
  picker). Use from /ui-test after login. Respects object.directCreate.
disable-model-invocation: true
---

# Create request

Need login first ([../login/SKILL.md](../login/SKILL.md)). Object name/slug from the user or from `projects/<project>/env/` / the change loop.

Inbox **Create** uses the **Create** button (`Common.Create`, plus icon) on the object grid or next to the tree — not GraphQL `Mutate_`.

Read `object.directCreate` from env/spec ([object-model.md](../../docs/entities/object-model.md)):

| Where you click Create | `directCreate` | What happens |
|------------------------|----------------|--------------|
| Object’s inbox grid | `true` | Skip object picker. If the object has **one** template, the new request form opens. If **several** templates, a **Templates** modal appears — pick one, **Continue**. |
| Object’s inbox grid | `false` / omitted | **Object-picker** modal (current object highlighted). Choose object (and template if asked), then continue. |
| Tree (no object selected) | — | Always the object-picker modal. |

## Steps

1. Open the object in the tree / inbox so the Create button is on **that** object’s grid when the user named an object.
2. Click **Create**.
3. Follow the table above. Do not invent extra clicks.
4. Success: request form is open (new request, fields visible, Save in the header). Title may still be empty until Save.

If Create is missing, the user may lack rights or the object is inactive — stop and say so.
