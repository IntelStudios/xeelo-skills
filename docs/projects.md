# Local projects (nested git)

**KB** = this repository except `projects/`. **One private git repo = the whole `projects/` directory.** Each Xeelo site is `projects/<name>/` (not its own git repo).

Site working copies (env, snapshots, change loops, GraphQL connection) must not appear in the public xeelo-skills repository. The public clone gitignores `/projects/` entirely — there is no `projects/README.md` in the KB, so `git clone <private> projects` can use an empty path.

Scripts and skills still use `projects/<name>/`. Pull KB updates in the xeelo-skills root; pull site updates inside `projects/`.

Do **not** use git submodules. Do **not** `git add -f projects/` in xeelo-skills. Forks of the KB stay empty of sites.

Copy [templates/projects-repo/](../templates/projects-repo/) into the private repo root (`.gitignore` + `README.md`). The parent xeelo-skills `.gitignore` does **not** apply inside `projects/.git` — without that nested ignore, `.xeelo-connection.json` and DB snapshots would be committed.

Version `env/` and `changes/`. Snapshot JSON files are gitignored; refresh them with `/download-db`.

## Setup A — empty `projects/` (fresh KB clone)

`projects/` is missing or empty. Either clone an existing private sites repo, or initialize one (see [Agent check](#agent-check) / [Initialize a nested repo](#initialize-a-nested-repo)):

```bash
git clone <private-url> projects
```

If the private repo has no template files yet:

```bash
cp templates/projects-repo/.gitignore templates/projects-repo/README.md projects/
```

## Setup B — `projects/` already has sites

This machine already has `lz/`, `ovnet/`, … under `projects/` with no nested git:

```bash
cd projects
cp ../templates/projects-repo/.gitignore ../templates/projects-repo/README.md .
git init
git add .
git commit -m "Initial projects repo"
```

Then host a **private** remote (GitHub, GitLab, …) and:

```bash
cd projects
git remote add origin git@<host>:<org>/<xeelo-projects>.git
git push -u origin main
```

## Agent check

Before creating a site, downloading a DB transfer, or otherwise using `projects/`:

1. Look at `projects/`. It is ready if it contains at least one site folder (`projects/<name>/`) **or** a nested `projects/.git`.
2. **If ready** — continue. A new site belongs in the same private repo.
3. **If not** (`projects/` missing, empty, or neither git nor a site):
   - Explain the intent (public KB, one private git for all sites, nested `.gitignore` for GraphQL connection files and snapshots).
   - **Offer** to initialize the nested repo. Do not run it until the user says yes. Do not silently create only `projects/<name>/`.
   - After init, tell the user to host a **private** remote themselves (the agent does not create the remote) and connect it.

Canonical init and remote commands: [Initialize a nested repo](#initialize-a-nested-repo).

## Initialize a nested repo

After the user agrees:

```bash
mkdir -p projects
cp templates/projects-repo/.gitignore templates/projects-repo/README.md projects/
cd projects
git init
```

Then the user hosts an empty **private** repository and:

```bash
cd projects
git remote add origin git@<host>:<org>/<xeelo-projects>.git
git add .
git commit -m "Initial projects repo"
git push -u origin main
```

`/new-project` adds `projects/<name>/` into this same private repo (including `conventions.md` from [`templates/project/conventions.md`](../templates/project/conventions.md)). Commit there, not in xeelo-skills.

## Site conventions

`projects/<name>/conventions.md` holds **site-specific** rules (language, naming, agent loop, other). The agent reads it at the start of site work. Template defaults: English canonical `name`, always Czech in `spec/language-table.yaml`, inbox/`onGrid` names stay English, **Agent loop** `ask` for `/publish` and `/download-db`. Edit per site; do not put these rules into the public KB.

**Agent loop** keys (`ask` | `auto`; missing = `ask`): **Publish after dry-run**, **Download-db after publish**. After a successful dry-run the agent offers `/publish` (and after publish `/download-db`) including “remember for this site”. Remember writes `auto` into that file. See [AGENT.md](../AGENT.md#agent-loop-in-conventions).
