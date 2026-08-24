# Site conventions

Read this file before creating or editing objects for this site.

## Naming

- Canonical `name` (and other default columns: object, tabs, sections, fields, roles, statuses, workflow, actions) in **English**.
- Do not put Czech or other languages into `name` or `code`.

## Localization

- Always add Czech in `spec/language-table.yaml` for user-visible labels: `object`, `tabs`, `sections`, `lines`, `workflow`, `roles`, `statuses`, `stepActions`, `objectActions`, `updateActions`, `objectMessages`, `templates`, `periodics`, `periodicActions`, `schedulers`.
- Inbox / `onGrid` column titles stay **English** — do not set `lines.<code>.onGrid` unless the user asks.
- Extra languages only when the user asks.
- After `/publish` of translations (or `/precompile` if the OT is already applied).

Platform details: parent xeelo-skills [docs/entities/localization.md](../../docs/entities/localization.md).

## Agent loop

Values: `ask` (default) or `auto`. Missing key = `ask`.

- **Publish after dry-run:** ask
- **Download-db after publish:** ask
- **Generate table comments:** ask

## Comments

- **Comment language:** en
- New entity → one description; change → append a dated changelog item; unchanged → skip.
- Simple tags only: `p`, `ul`/`ol`/`li`, `strong`/`em`, `br`, `a`.

## Other

(Add site-specific rules here.)
