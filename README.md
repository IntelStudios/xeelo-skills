# XeeloKB

Agent-oriented knowledge base for Xeelo configuration: **download DB transfer → env specs → change-loop Object Transfer**.

## Quick start

1. Read **[AGENT.md](AGENT.md)** — playbook
2. If `projects/` is empty or missing, set up the nested private repo — **[docs/projects.md](docs/projects.md)**
3. Per project (`projects/<name>/` = one Xeelo):
   - Copy `.xeelo-connection.example.json` → `.xeelo-connection.json` and fill credentials
   - `make download-ovnet` / `python scripts/download-db-transfer.py --connection ...`
   - `make extract-ovnet`
   - `make loop-init SLUG=... OBJECTS="ov-net-customer"`
   - Edit `changes/<slug>/objects/...` then `make generate-loop LOOP=...`
4. Upload generated ZIP in Xeelo Admin → **Object Transfer** → select rows → process

Greenfield OT sample (no DB download):

```bash
make generate-account
make validate-account
```

## Read vs generate

| | DB Transfer | Object Transfer |
|---|-------------|-----------------|
| **XeeloKB reads** | Download + parse → `env/` | OT → spec extract |
| **XeeloKB generates** | No | **Yes** — change-loop ZIPs |
| **Deploy** | Full site replace (Admin) | **Partial** — batch by row selection |

## Regenerate data from source repos

```bash
make extract
make generate-account
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
| [data/](data/) | Schemas, enums, hints, object-transfer-map |
| [scripts/download-db-transfer.py](scripts/download-db-transfer.py) | Admin async download |
| [scripts/push-object-transfer.py](scripts/push-object-transfer.py) | Admin OT upload + process |
| [scripts/publish-precompile.py](scripts/publish-precompile.py) | Admin PreCompileSettings |
| [scripts/extract-db-transfer-to-env.py](scripts/extract-db-transfer-to-env.py) | DB → env |
| [scripts/generate-change-loop.py](scripts/generate-change-loop.py) | Loop → OT ZIPs |

## Spec v2 highlights

- **Multiple tabs** (left/right) and **sections** per tab
- **onGrid** — inbox grid field flags + layout placements
- **subgrids** — ObjectSub trees on object specs
- **Object transfer** output with hierarchy (`ObjectSetup` / `ObjectMap`)
