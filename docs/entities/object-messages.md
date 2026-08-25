# Object Messages

Localized HTML banners shown in User GUI as a **modal** before the user continues a create/update save or a workflow action. The user can **Cancel** (abort) or **Continue**.

Schemas: [`ObjectMessage.json`](../data/schemas/ObjectMessage.json), [`ObjectMessageCondition.json`](../data/schemas/ObjectMessageCondition.json) · styles: [`ObjectMessageStyle.json`](../data/enums/ObjectMessageStyle.json)

Spec fragment: [`spec/object-messages.yaml`](../transfer/spec-format.md#object-messages-specobject-messagesyaml)

## Do not confuse

| Entity | Purpose |
|--------|---------|
| **ObjectMessage** | HTML content + style + optional field conditions (owned by Object) |
| **ObjectUpdateMessage** | Junction: show that message on one **update action** (`IsVisible`) |
| **ObjectDefaultMessage** | Junction: show on **create** (template). Site refresh inserts rows at `IsVisible=0` |
| **WorkflowMessage** / **WorkflowStepMessage** | Same ObjectMessage, shown on submitted workflow actions |
| **WorkflowStepSuccessMessage** | Toast after a step action — different entity |
| **Notification** | Email template (subject + HTML body). Not a form modal. [notifications.md](notifications.md) |

## User GUI

On **Save** of a new request (create **or** update version, `IsNew`) and on **workflow** actions, User loads eligible message IDs, then opens a modal with the HTML (sanitized as HTML).

| Control | Behaviour |
|---------|-----------|
| **Cancel** | Abort further save / workflow. On create/update the request is not submitted. |
| **Continue** | Proceed. **Disabled** when any shown message has style **Error** (`IsError=1`) **and** the request is new/update. |

Use **Warning** when the user must be told something and still be allowed to save (Cancel remains). Use **Error** only to block Continue on the new form.

HTML is localized (`LanguageTable` ColumnName **`ObjectMessageFormat`**). Canonical English HTML lives on the row. The DB column is misspelled **`ObjectMessageFromat`**; transfers must use that column name. User precompile and LanguageTable use `ObjectMessageFormat`.

Placeholders in the HTML (`{…}`) are formatted from the current request when the cached body looks dynamic.

## Admin UI

Object Detail → **Messages**:

1. Name, order, **style** (Information / Warning / Error), HTML body (globe = translation)
2. **Conditions** — same type catalog as update-action conditions (OR per line)
3. **Visibility** — which templates, update actions, workflows, and workflow steps show the message

Update Action → Access → **Messages** is the same junction (`ObjectUpdateMessageIsVisible`).

## Data model

```text
Object (1) ──< ObjectMessage (N)
                    ├── ObjectMessageStyleID → ObjectMessageStyle (seed, not transferred)
                    ├── ObjectMessageFromat  (canonical HTML)
                    └──< ObjectMessageCondition (optional)

ObjectUpdateAction ──< ObjectUpdateMessage ──> ObjectMessage
ObjectDefault       ──< ObjectDefaultMessage ──> ObjectMessage
Workflow            ──< WorkflowMessage ──> ObjectMessage
WorkflowStep        ──< WorkflowStepMessage ──> ObjectMessage
```

### Styles (seed)

| ID | Name | CSS | `IsError` | Spec `style` |
|----|------|-----|-----------|--------------|
| 1 | Information | SUCCESS | 0 | `information` |
| 2 | Warning | WARNING | 0 | `warning` |
| 3 | Error | DANGER | 1 | `error` |

`ObjectMessageStyle` is **not** in Object Transfer (site seed).

### When a message is listed

Unsubmitted request (`RequestIsSubmitted = 0`):

- Update version (`ObjectUpdateActionID` set) → visible `ObjectUpdateMessage` rows for that action
- Create → visible `ObjectDefaultMessage` rows for the template

Submitted request → workflow / workflow-step junctions.

Conditions: same OR-per-line rule as update-action conditions (`fnRequestLineDataCondition`). No conditions → always listed once the junction is visible.

## Transfer / spec

| In Object Transfer | Not in transfer |
|--------------------|-----------------|
| `ObjectMessage`, `ObjectMessageCondition`, `ObjectUpdateMessage` | `ObjectMessageStyle`, `ObjectMessageConditionType`; `ObjectDefaultMessage` is usually left to site refresh (`IsVisible=0`) |

Emit `ObjectMessage` rows from `spec/object-messages.yaml`. Linking only `updateActions[].messages[].key` without that fragment assumes the `ObjectMessage` row already exists on the site (Orig. ID in `ids.explicit.objectMessages`).

Czech (or other) HTML: `languageTable.objectMessages.<key>.html.<lang>`. Name: `languageTable.objectMessages.<key>.<lang>`.

## Recipe

[`add-update-action.md`](../../recipes/add-update-action.md) — attach a warning on the update form.
