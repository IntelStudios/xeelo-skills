# Site conventions

Read this file before creating or editing objects for this site.

## Naming

- Canonical `name` (and other default columns: object, tabs, sections, fields, roles, statuses, workflow, actions) in **English**.
- Do not put Czech or other languages into `name` or `code`.

## Localization

- Always add Czech in `spec/language-table.yaml` for user-visible labels: `object`, `tabs`, `sections`, `lines`, `workflow`, `roles`, `statuses`, `stepActions`, `objectActions`, `updateActions`, `templates`.
- Inbox / `onGrid` column titles stay **English** — do not set `lines.<code>.onGrid` unless the user asks.
- Extra languages only when the user asks.
- After `/push` of translations, **/publish**.

Platform details: parent XeeloKB [docs/entities/localization.md](../../docs/entities/localization.md).

## Other

(Add site-specific rules here.)
