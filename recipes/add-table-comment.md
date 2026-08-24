# Add Admin table comments

Attach **HTML comments** (`TableComments`) to configuration entities (object, lines, periodics, …). Not request comments.

Entity reference: [docs/entities/comments.md](../docs/entities/comments.md). Spec: [spec-format.md](../docs/transfer/spec-format.md#admin-comments-speccommentsyaml).

## Preconditions

- Parent entity exists in the same spec (or already on the site with an Orig. ID in `ids.explicit`)
- Site conventions **Generate table comments** is `auto`, or the user picked a generate option (`ask`)

## Ask

Follow **Generate table comments** in `projects/<name>/conventions.md` (`ask` | `auto`; missing = `ask`). Offer only after spec edits, **before** `generate-change-loop.py`:

- **Generate comments now**
- **Generate now and remember for this site** (set that key to `auto`)
- **Skip comments**

## Admin UI path

1. Open the entity in Admin
2. Comments portlet → Add → Froala HTML → Save

## Spec / Object Transfer path

Fragment `spec/comments.yaml`:

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

Include in `xeelo-spec.yaml`:

```yaml
includes:
  - spec/object.yaml
  - spec/comments.yaml
  - spec/ids.yaml
```

Simple HTML only: `p`, `ul`/`ol`/`li`, `strong`/`em`, `br`, `a`. Default `userName` is `xeelo-skills`. New comments get a new `TableCommentID` (`ids.explicit.tableComments`, key `TableName:entityKey:index`).

Content:

- **New entity** — one description (what the field/action is for)
- **Change** — append a dated changelog item; do not edit older items
- **Unchanged** — do not add a comment

Language: **Comment language** in conventions (`en` | `cs` | …; missing = `en`).

Generate:

```bash
python scripts/generate-change-loop.py projects/<project>/changes/<slug>
```

**Transfer scope:** `TableComments` only for the listed parents. Object Transfer upserts by Orig. ID; omitted comments stay on the site.

## Checklist

- [ ] Parent keys match `languageTable` / spec keys (`lines.<code>`, `periodics.<key>`, …)
- [ ] HTML is a short description or a dated changelog append
- [ ] No `script` / `iframe` / inline styles beyond simple tags
- [ ] Recycled workflow: do not comment shared `workflow` / `roles` / `statuses` / `stepActions`
- [ ] After generate, dry-run then `/publish` per conventions
