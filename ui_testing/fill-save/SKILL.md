---
name: ui-test-fill-save
description: >-
  Fill User UI request fields from spec (first wave: text, number, combo) and
  Save. Use from /ui-test on an open request form. Stop on unsupported types.
disable-model-invocation: true
---

# Fill and Save

Need an open request form ([../create-request/SKILL.md](../create-request/SKILL.md) or inbox open). Field list: user message, or required fields from `projects/<project>/env/objects/<slug>/` / the change-loop spec.

Type → widget: [../reference/field-types.md](../reference/field-types.md).

## First wave

Fill only **text**, **number**, and **combo** (`combobox`, `combobox_search`, `combobox_server` as a combo). Use labels from the form (LanguageTable / spec `name`).

If a **required** field is another type (date, memo, attachment, subgrid, …): **stop**, name the field and type, point at `field-types.md`. Do not guess.

Lookups that auto-fill after a combo/text change: wait for the value; do not overwrite unless the user said to.

## Save

Save is in the **request header** (green **Save**, `Common.Save`), not a form footer.

- Prefer **Save** (stay on the request).
- If the control is a split button, the extra item is **Save & close** (`Common.SaveAmpClose`) — use it only when the user asked to close.

Wait for the save to finish (spinner gone, no validation banner).

**Success:** request stays open (unless Save & close); title / autonumber may appear; no blocking validation message.

**Fail:** mandatory-field warning, calculation error, or the form did not accept the value — report visible text. Do not retry blindly more than once.
