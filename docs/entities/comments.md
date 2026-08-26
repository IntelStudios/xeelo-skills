# Admin comments (TableComments)

Admin can attach **HTML comments** to most configuration entities. This is **not** a column on the entity, not request comments, and not GraphQL. Storage is **`TableComments`**: `(TableName, TableRowID)` → HTML body, same polymorphic pattern as `LanguageTable`.

Schema: [`data/schemas/TableComments.json`](../data/schemas/TableComments.json) · spec: [`spec/comments.yaml`](../transfer/spec-format.md#admin-comments-speccommentsyaml) · recipe: [`recipes/add-table-comment.md`](../../recipes/add-table-comment.md)

## How it is stored

| Piece | Where |
|-------|--------|
| Parent | `TableName` (SQL table, e.g. `ObjectLine`) + `TableRowID` (parent PK as int) |
| Body | `TableCommentData` (HTML, `nvarchar(max)`) |
| Author | `UserName` (Admin login, or `xeelo-skills` from generate). `UserID` is `0` |
| When | `TableCommentDate` (required) |
| Attachment | `AttachmentID` (optional; omit in OT, site default `-1`) |
| Identity | `TableCommentID` (Orig. ID) |

Several comments per parent. Admin grid is newest first. Spec lists are **oldest first** so new changelog entries append.

## Admin UI

Most site editors show a comments portlet (`enableComments` default **true**). SuperAdmin lists and some log screens turn it off. Editor is Froala HTML. REST is `GET/POST/PUT` on the site Admin Comment API. Insert sets `UserID=0` and `UserName` from the logged-in admin. Edit sanitizes HTML strictly. Object Transfer JSON upload writes rows directly (no sanitizer) — still emit **simple tags only**: `p`, `ul`/`ol`/`li`, `strong`/`em`, `br`, `a`.

## Object Transfer

`TableComments` is in Object Setup JSON upload. Sync is **delete + insert by `TableCommentID`** (identity insert). Object Transfer is a **delta**:

- Omit a comment row → site copy stays
- Same Orig. ID, different HTML → that comment is replaced
- New Orig. ID → new comment (append)

xeelo-skills does **not** post comments through REST or GraphQL. Generate emits `TableComments` rows (and XML parent→`TableComments` edges). `object-transfer-map.json` has no parent→child edge (polymorphic, like LanguageTable).

## Spec: `spec/comments.yaml`

Keys match [`languageTable`](localization.md) entity types. Values are **lists** of `{ html, userName?, date? }`.

```yaml
comments:
  object:
    - html: "<p>FIO accounts that drive payment import.</p>"
  lines:
    TYPE:
      - html: "<p>Payment source. Hourly periodic matches FIO.</p>"
  periodics:
    load_fio_hourly:
      - html: "<p>2026-08-24: hourly scheduler → load_transactions 9016.</p>"
```

| Spec key | Parent table |
|----------|----------------|
| `object` | `Object` |
| `company` | `Company` |
| `objectType` | `ObjectType` |
| `workflow` | `Workflow` |
| `tabs.<TabName>` | `ObjectLineTab` |
| `sections.<TabName>/<SectionName>` | `ObjectLineSection` |
| `lines.<code>` | `ObjectLine` |
| `templates.<key>` | `ObjectDefault` |
| `roles.<key>` / `statuses.<key>` | `Role` / `RequestStatus` |
| `stepActions.<stepName>/<actionName>` | `WorkflowStepAction` |
| `objectActions.<key>` / `updateActions.<key>` | action row |
| `periodics.<key>` | `Periodic` |
| `periodicActions.<periodicKey>/<actionKey>` | `PeriodicAction` |
| `schedulers.<periodicKey>` | `Scheduler` |
| `objectMessages.<key>` | `ObjectMessage` |
| `templateHints.<templateKey>.<code>` | `ObjectDefaultLine` |

`ObjectSub*` parents are **not** in `comments.yaml` yet.

`userName` defaults to **`xeelo-skills`**. `date` on generate defaults to generate time; extract keeps `TableCommentDate`. Recycled workflow (`workflow.reuse: true`) skips `workflow` / `roles` / `statuses` / `stepActions` comments (same as LanguageTable).

**IDs:** `ids.explicit.tableComments` keyed `TableName:entityKey:index` (e.g. `ObjectLine:TYPE:0`).

Extract writes the fragment only when comments exist for this object’s owned rows.

## Agent loop

Whether the agent **writes** HTML into `spec/comments.yaml` is a site convention, not a generator flag. See [AGENT.md § Agent loop](../../AGENT.md#agent-loop-in-conventions) **Generate table comments**. After spec edits, **before** generate:

- New entity → one description comment
- Changed entity → **append** a changelog comment (do not rewrite older list items)
- Unchanged entity → skip

Language: **Comment language** in `projects/<name>/conventions.md` (`en` | `cs` | …; missing = `en`).

## Related

- Request-level comments and `WorkflowStepActionIsCommented` (comment required on a step action) are **not** this table.
- Translated labels: [localization.md](localization.md)
