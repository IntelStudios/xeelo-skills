# Xeelo Knowledge Base

**KB** = this repository **except** `projects/` and `internal/`. When the user asks what the KB contains or what it says, answer only from `docs/`, `recipes/`, `data/`, `scripts/`, `AGENT.md`, skills — not from `projects/` or `internal/`. You may draw from `projects/` when implementing; they are site working copies, not KB. If `internal/` exists, read it when the KB is incomplete or when re-verifying platform behaviour; write extracted facts into the public KB **only in `project-kb` work mode** (`internal/work-mode.md`; missing file → `project`), do not copy source paths into `docs/` or `recipes/`.

**Check `projects/` first** before creating a site, downloading a DB transfer, or otherwise using that tree. If it has no site folder and no nested `projects/.git`, explain the nested-repo intent (public KB; one private git = all sites) and **offer** to initialize it — do not silently scaffold `projects/<name>/`. The user hosts the private remote. See [docs/projects.md](docs/projects.md).

When the user asks to create or modify Xeelo objects, workflows, or transfers:

1. Read [AGENT.md](AGENT.md) first
2. Prefer project loop: download DB transfer → extract `env/` → edit `changes/<slug>/` → generate Object Transfer. After generate, **ask** whether to `/push` and `/publish` — do not run them unless the user says yes.
3. In each `changes/<slug>/`, keep `tasks.md` as a checklist and write/update **`notes.md`** for the next human/agent: **Requested** (user ask; prompt/plan excerpts OK, not the whole chat) vs **Done** (what actually changed). Update on later rounds in the same loop; do not silently rewrite history.
4. Connection: `projects/<project>/.xeelo-connection.json` (gitignored) with `adminBaseUrl`, `siteId` (`XA-SITE-ID`), credentials
5. Specs: `xeelo-spec.yaml` v2 — tabs → sections → fields + optional onGrid / subgrids
6. Use [data/schemas/](data/schemas/) and [data/object-transfer-map.json](data/object-transfer-map.json)
7. Generate change packages with `python scripts/generate-change-loop.py projects/<project>/changes/<slug>`
8. Samples: [projects/ovnet/](projects/ovnet/), [projects/account-object/](projects/account-object/)

**Skills** live in [`.agents/skills/`](.agents/skills/). When the user invokes `/new-project`, asks for a new Xeelo project/site, invokes `/download-db`, or asks to download/refresh/pull a DB transfer or sync env from Admin, invokes `/push` or asks to push/upload/deploy an Object Transfer, invokes `/publish` or asks to publish/precompile settings, **read** the matching `SKILL.md` and follow it:

- [`.agents/skills/new-project/SKILL.md`](.agents/skills/new-project/SKILL.md)
- [`.agents/skills/download-db/SKILL.md`](.agents/skills/download-db/SKILL.md)
- [`.agents/skills/push/SKILL.md`](.agents/skills/push/SKILL.md)
- [`.agents/skills/publish/SKILL.md`](.agents/skills/publish/SKILL.md)

**New project:** after the `projects/` check, create `projects/<name>/` + empty `snapshots/`, `env/`, `changes/` + `.xeelo-connection.json` with **empty** `siteId` and `credentials` (never copy from other projects). Infer `adminBaseUrl` as `https://<name>.xeeloadmin.online/` only when reasonable; then tell the user what to fill in — see [AGENT.md § Creating a new project](AGENT.md). Commit in the nested `projects/` repo, not in XeeloKB.

**Combo-box:** **reference** = ObjectLineSource on ObjectLine (číselník; system / values / refObject). **lookup** = ObjectLineLookup on template (dotazovací mapa). New `sources.*` default **`styleId: 4`** (Value). See [AGENT.md](AGENT.md). If `internal/` exists, use it when the KB is incomplete.

**Description memo:** new `description_memo` fields default **`descMemoBorder: false`** (omit or false). Set `true` only when the user wants a visible box.

**Read** DB transfers (download + parse into env). **Generate** Object Transfer only (partial deploy). Do not generate DB transfer ZIPs.
