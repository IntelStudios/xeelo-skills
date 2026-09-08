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
  subgrids:
    invoice_lines:
      lines:
        DESC:
          - html: "<p>2026-09-08 (Milan Krejčík): Line description on the subgrid.</p>"
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
| `subgrids.<key>.lines.<code>` | `ObjectSubLine` |
| `templates.<key>` | `ObjectDefault` |
| `roles.<key>` / `statuses.<key>` | `Role` / `RequestStatus` |
| `stepActions.<stepName>/<actionName>` | `WorkflowStepAction` |
| `objectActions.<key>` / `updateActions.<key>` | action row |
| `periodics.<key>` | `Periodic` |
| `periodicActions.<periodicKey>/<actionKey>` | `PeriodicAction` |
| `schedulers.<periodicKey>` | `Scheduler` |
| `objectMessages.<key>` | `ObjectMessage` |
| `templateHints.<templateKey>.<code>` | `ObjectDefaultLine` |

`ObjectSub*` parents other than **`ObjectSubLine`** (`comments.subgrids.<key>.lines.<code>`) are not in `comments.yaml` yet.

`userName` defaults to **`xeelo-skills`**. `date` on generate defaults to generate time; extract keeps `TableCommentDate`. Recycled workflow (`workflow.reuse: true`) skips `workflow` / `roles` / `statuses` / `stepActions` comments (same as LanguageTable).

**IDs:** `ids.explicit.tableComments` keyed `TableName:entityKey:index` (e.g. `ObjectLine:TYPE:0`).

Extract writes the fragment only when comments exist for this object’s owned rows.

## Agent loop

Whether the agent **writes** HTML into `spec/comments.yaml` is a site convention, not a generator flag. See [AGENT.md § Agent loop](../../AGENT.md#agent-loop-in-conventions) **Generate table comments**. After spec edits, **before** generate:

- New entity → one description comment
- Changed entity → **append** a changelog comment (do not rewrite older list items)
- Unchanged entity → skip

Language: **Comment language** in `projects/<name>/conventions.md` (`en` | `cs` | …; missing = `en`).

HTML for a **new** entity or a **changelog** item includes the **requestor’s full name** after the date. The name comes from gitignored `projects/<site>/.xeelo-connection.json` → **`commentRequestor`** (per developer; several people can share one site). Empty → ask once and write it there. Do not use Cursor first-name-only user info. Do not put the person’s name in `conventions.md`. If this change was requested by someone else, ask and use that name in the HTML for this item only.

```html
<p>2026-09-08 (Milan Krejčík): List of Assets on-grid shows Asset status as colored badges.</p>
```

Never given name only. Put the comment on the **changed line** (`comments.lines.<code>` or `comments.subgrids.<key>.lines.<code>`) when the change is a field; use `comments.object` only when the change is object-wide.

## Related

- Request-level comments and `WorkflowStepActionIsCommented` (comment required on a step action) are **not** this table.
- Translated labels: [localization.md](localization.md)
