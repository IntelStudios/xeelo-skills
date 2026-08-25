---
name: new-project
description: >-
  Scaffold a new empty Xeelo site project under projects/<name>/ with
  snapshots, env, changes folders and .xeelo-connection.json template.
  Use when the user asks to create a new Xeelo project, site, or workspace
  folder, or invokes /new-project.
disable-model-invocation: true
---

# New Xeelo Project

Scaffold `projects/<name>/` for one Xeelo site. Read [AGENT.md](../../../AGENT.md) for the full playbook. Nested git: [docs/projects.md](../../../docs/projects.md).

## Inputs

Determine from the user message or ask once:

- **`<name>`** — project slug under `projects/`. Must be a valid directory name.
- **`xeeloUrl`** — optional. Infer `https://<name>.xeelo.online/` only when the slug clearly matches the site hostname; otherwise leave empty for the user to fill.

## Steps

0. **Check `projects/`** (required). Ready = at least one site folder (`projects/<other>/`) **or** nested `projects/.git`. If missing, empty, or neither git nor a site:
   - Explain: public xeelo-skills has no sites; one **private** git repo = the whole `projects/` directory; GraphQL connection files and DB snapshots stay out of that git via [templates/projects-repo/.gitignore](../../../templates/projects-repo/.gitignore).
   - **Offer** to initialize the nested repo. Do **not** run it until the user says yes. Do **not** scaffold `projects/<name>/` first.
   - If they agree: `mkdir -p projects`, copy `templates/projects-repo/.gitignore` and `README.md` into `projects/`, `git init` inside `projects/`. Then tell them to host a **private** remote (GitHub/GitLab/… — you do not create the remote) and:

     ```bash
     cd projects
     git remote add origin git@<host>:<org>/<xeelo-projects>.git
     git add .
     git commit -m "Initial projects repo"
     git push -u origin main
     ```

   Canonical copy: [docs/projects.md](../../../docs/projects.md).

1. **Verify** `projects/<name>/` does not already exist. If it does, stop and ask whether to extend the existing project instead.

2. **Create layout:**

   ```text
   projects/<name>/
     conventions.md
     snapshots/.gitkeep
     env/.gitkeep
     changes/.gitkeep
     .xeelo-connection.json
   ```

   Copy [`templates/project/conventions.md`](../../../templates/project/conventions.md) to `projects/<name>/conventions.md`.

3. **Write** `.xeelo-connection.json` with **empty placeholder values**. Never copy `token` from other projects.

   ```json
   {
     "xeeloUrl": "https://<name>.xeelo.online/",
     "token": ""
   }
   ```

   Use inferred URL when confident; otherwise set `"xeeloUrl": ""`.

4. **Do not** create `.xeelo-connection.example.json`.

5. **Do not** download DB transfer or extract env until the user has filled connection details.

## After creation — report this checklist

| Field | Where to get it |
|-------|-----------------|
| `xeeloUrl` | Xeelo site URL (User UI), e.g. `https://<name>.xeelo.online/` |
| `token` | GraphQL access token with **`isAdmin`** (from site GraphQL access tokens). Fixed; no refresh. |

Remind the user that `.xeelo-connection.json` is gitignored, and that the new site folder should be committed in the nested `projects/` repo (not xeelo-skills). Next step after filling connection: `/download-db`.
