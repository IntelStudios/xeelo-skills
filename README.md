# xeelo-skills

Agent-oriented knowledge base for Xeelo configuration: **download DB transfer → env specs → change-loop Object Transfer**.

## Quick start

1. Read **[AGENT.md](AGENT.md)** — playbook
2. If `projects/` is empty or missing, set up the nested private repo — **[docs/projects.md](docs/projects.md)**
3. Per project (`projects/<name>/` = one Xeelo):
   - Write `projects/<name>/.xeelo-connection.json` with `xeeloUrl` and GraphQL `token`
   - `python scripts/download-db-transfer.py --connection projects/<name>/.xeelo-connection.json`
   - `python scripts/extract-db-transfer-to-env.py <snapshot.json> -o projects/<name>/env`
   - `python scripts/init-change-loop.py --project projects/<name> --slug <slug>`
   - Edit `changes/<slug>/objects/...` then `python scripts/generate-change-loop.py projects/<name>/changes/<slug>`
4. After generate the loop dry-runs the OT (`--only-test`). **`/publish`** applies it and precompiles (`ask` unless the site’s `conventions.md` says `auto`). Same for **`/download-db`** after a successful publish.

## Read vs generate

| | DB Transfer | Object Transfer |
|---|-------------|-----------------|
| **xeelo-skills reads** | Download + parse → `env/` | OT → spec extract |
| **xeelo-skills generates** | No | **Yes** — change-loop JSON |
| **Deploy** | Full site replace | **Partial** — `/publish` applies generated OT JSON |

## Regenerate data from source repos

```bash
make extract
```

Env vars: `XEELO_ADMIN_REPO`, `XEELO_USER_REPO` (defaults: sibling repos under `/data/src/`)

## Structure

**KB** is everything in this repo **except** `projects/`. Site folders under `projects/` are working copies (gitignored; one private git repo). They are not KB content. See [docs/projects.md](docs/projects.md).

| Path | Purpose |
|------|---------|
| [AGENT.md](AGENT.md) | Agent playbook |
| [docs/projects.md](docs/projects.md) | Nested private git for `projects/` |
| [docs/transfer/object-transfer-format.md](docs/transfer/object-transfer-format.md) | OT output format |
| [docs/transfer/db-transfer-format.md](docs/transfer/db-transfer-format.md) | DB transfer + download protocol |
| [docs/transfer/spec-format.md](docs/transfer/spec-format.md) | Spec v2 language |
| [recipes/](recipes/) | Generation patterns |
| `projects/` | One folder per Xeelo site (not KB; gitignored — [docs/projects.md](docs/projects.md)) |
| [data/](data/) | Schemas, enums, hints, object-transfer-map, Font Awesome catalog |
| [scripts/download-db-transfer.py](scripts/download-db-transfer.py) | GraphQL DB-transfer download |
| [scripts/push-object-transfer.py](scripts/push-object-transfer.py) | GraphQL OT JSON upload (dry-run `--only-test` → `isTest`) |
| [scripts/publish-object-transfer.py](scripts/publish-object-transfer.py) | Real OT upload (`isTest: false`) + precompile |
| [scripts/precompile-settings.py](scripts/precompile-settings.py) | GraphQL precompile only |
| [scripts/extract-db-transfer-to-env.py](scripts/extract-db-transfer-to-env.py) | DB → env |
| [scripts/generate-change-loop.py](scripts/generate-change-loop.py) | Loop → OT JSON |

## Spec v2 highlights

- **Multiple tabs** (left/right) and **sections** per tab
- **onGrid** — inbox flags + placement; catalog and new-object default in [docs/entities/ongrid.md](docs/entities/ongrid.md)
- **subgrids** — ObjectSub trees on object specs
- **Object transfer** output as JSON (table → rows, same shape as DB download)
