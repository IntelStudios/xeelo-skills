# Xeelo Knowledge Base

**KB** = this repository **except** `projects/` and `internal/`. When the user asks what the KB contains or what it says, answer only from `docs/`, `recipes/`, `data/`, `scripts/`, `AGENT.md`, skills — not from `projects/` or `internal/`. You may draw from `projects/` when implementing; they are site working copies, not KB. If `internal/` exists, read it when the KB is incomplete or when re-verifying platform behaviour; write extracted facts into the public KB **only in `project-kb` work mode** (`internal/work-mode.md`; missing file → `project`), do not copy source paths into `docs/` or `recipes/`.

**Check `projects/` first** before creating a site, downloading a DB transfer, or otherwise using that tree. If it has no site folder and no nested `projects/.git`, explain the nested-repo intent (public KB; one private git = all sites) and **offer** to initialize it — do not silently scaffold `projects/<name>/`. The user hosts the private remote. See [docs/projects.md](docs/projects.md).

When the user asks to create or modify Xeelo objects, workflows, or transfers:

1. Read [AGENT.md](AGENT.md) first
2. Prefer project loop: download DB transfer → extract `env/` → edit `changes/<slug>/` → generate Object Transfer. After generate, **dry-run** `--only-test`, then `/publish` per `projects/<name>/conventions.md` (**Publish after dry-run:** `ask` → offer this loop / this+remember / skip; `auto` → run and announce). Same for `/download-db` after successful publish. After spec edits, **Generate table comments** the same way (`spec/comments.yaml`).
3. In each `changes/<slug>/`, keep `tasks.md` as a checklist and write/update **`notes.md`** for the next human/agent: **Requested** (user ask; prompt/plan excerpts OK, not the whole chat) vs **Done** (what actually changed). Update on later rounds in the same loop; do not silently rewrite history.
4. Connection: `projects/<project>/.xeelo-connection.json` (gitignored) with `xeeloUrl` and GraphQL `token`
5. Specs: `xeelo-spec.yaml` v2 — tabs → sections → fields + optional onGrid / subgrids. YAML key order must match OT extract ([spec-format.md](docs/transfer/spec-format.md#yaml-key-order)); after spec edits run `python scripts/normalize-spec-yaml.py`.
6. Use [data/schemas/](data/schemas/) and [data/object-transfer-map.json](data/object-transfer-map.json)
7. Generate change packages with `python scripts/generate-change-loop.py projects/<project>/changes/<slug>`

**Skills** live in [`.agents/skills/`](.agents/skills/). When the user invokes `/new-project`, asks for a new Xeelo project/site, invokes `/download-db`, or asks to download/refresh/pull a DB transfer or sync env from the site, invokes `/publish` or asks to publish/deploy an Object Transfer, invokes `/precompile` or asks to precompile settings only, invokes `/graphql` or asks to query/mutate GraphQL (`Select_` / `Mutate_`, ticket counts, `access_rights`, header filters such as `createdDate`), invokes `/sync-main` or asks to regularly check/pull/sync **xeelo-skills `main`**, **read** the matching `SKILL.md` and follow it **before** product source:

- [`.agents/skills/new-project/SKILL.md`](.agents/skills/new-project/SKILL.md)
- [`.agents/skills/download-db/SKILL.md`](.agents/skills/download-db/SKILL.md)
- [`.agents/skills/publish/SKILL.md`](.agents/skills/publish/SKILL.md)
- [`.agents/skills/precompile/SKILL.md`](.agents/skills/precompile/SKILL.md)
- [`.agents/skills/graphql/SKILL.md`](.agents/skills/graphql/SKILL.md)
- [`.agents/skills/sync-main/SKILL.md`](.agents/skills/sync-main/SKILL.md)

**New project:** after the `projects/` check, create `projects/<name>/` + empty `snapshots/`, `env/`, `changes/` + `.xeelo-connection.json` with **empty** `token` (never copy from other projects). Infer `xeeloUrl` as `https://<name>.xeelo.online/` only when reasonable; then tell the user what to fill in — see [AGENT.md § Creating a new project](AGENT.md). Commit in the nested `projects/` repo, not in xeelo-skills.

**Combo-box:** **reference** = ObjectLineSource on ObjectLine (číselník; `spec/references.yaml`). **lookup** = ObjectLineLookup query map on template (`spec/lookups.yaml` + `sourceField`). Combo always needs a reference; lookup may sit on the same field. New `references.*` default **`styleId: 4`** (Value). See [AGENT.md](AGENT.md). If `internal/` exists, use it when the KB is incomplete.

**Autonumber:** site sequence (`spec/autonumbers.yaml`) bound on the template line; **unique** is `fields[].uniqueId` (1–4) on ObjectLine. Typical request identifier: text + autonumber + `uniqueId: 1`. See [AGENT.md](AGENT.md) and [docs/entities/object-model.md](docs/entities/object-model.md).

**Description memo:** new `description_memo` fields default **`descMemoBorder: false`** (omit or false). Set `true` only when the user wants a visible box.

**Labels:** canonical `name` in English; translations in `spec/language-table.yaml`. Read `projects/<name>/conventions.md` when present. See [AGENT.md](AGENT.md) and [docs/entities/localization.md](docs/entities/localization.md).

**Admin comments:** `spec/comments.yaml` (`TableComments` HTML). Follow **Generate table comments** in conventions (`ask` default). See [docs/entities/comments.md](docs/entities/comments.md).

**Tree icon / color:** Font Awesome **6.5.1** class string on `object.icon` / `objectType.icon` / `company.icon` (search `python scripts/search-fa-icons.py --query bank`; local [`data/fontawesome-icons.json`](data/fontawesome-icons.json)). Color = existing `CustomColorCode` on `object.color` / `objectType.color` (not HEX). Do not spec obsolete `CompanyTreeColor` or `ObjectTypeTreeColorFont`. See [AGENT.md](AGENT.md) and [spec-format.md](docs/transfer/spec-format.md#tree-icons-and-colors).

**New object workflow:** always ask whether to create a **new** workflow or **reuse** an existing one (list from site `env/`: object — name — id). Reuse = `workflow.reuse: true`. OT JSON is a delta vs download: unchanged entity rows are omitted even when FKs still reference them. Do not silent-default `workflow.mode: minimal`. See [AGENT.md § Ask which workflow](AGENT.md#ask-which-workflow).

**Update action workflow:** always ask which workflow the new request version should use. **Default (Recommended)** = default `ObjectDefault` workflow — omit `updateActions[].workflow`. See [AGENT.md](AGENT.md) and [recipes/add-update-action.md](recipes/add-update-action.md).

**Read** DB transfers (download + parse into env). **Generate** Object Transfer only (partial deploy). Do not generate DB transfer ZIPs.
