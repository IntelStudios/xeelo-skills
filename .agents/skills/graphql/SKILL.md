---
name: graphql
description: >-
  Load live GraphQL schema and access_rights from POST {xeeloUrl}/graphql and
  save them under projects/<project>/graphql/. Use when the user wants to
  query or mutate GraphQL, run Select_ / Mutate_, count tickets, filter headers
  (created / createdDate), inspect access_rights, or invokes /graphql. Not for
  admin transfer (/download-db, /publish, /precompile).
disable-model-invocation: true
---

# GraphQL (live schema + access_rights)

When the user wants to use site GraphQL (`Select_` / `Mutate_`, ticket counts, header filters, `access_rights`), **read this skill first**. Load schema and rights from `POST {xeeloUrl}/graphql` — do not guess filter shapes from product source. Admin transfer stays `/download-db`, `/publish`, `/precompile`.

GET `{xeeloUrl}/graphql` is Apollo Sandbox (HTML). Schema comes from **POST** introspection.

## Prerequisites

- `projects/<project>/.xeelo-connection.json` exists and is filled in:
  - `xeeloUrl` — Xeelo site URL (User UI)
  - `token` — GraphQL Bearer token (`isAdmin` for admin ops; any GraphQL token for `access_rights` / `Select_`)
- If the connection file is missing or `xeeloUrl` / `token` is empty, stop and tell the user to complete it first (see `/new-project` checklist). If the loader rejects the file, tell the user to **replace** it with `{ "xeeloUrl": "...", "token": "..." }`.

## Inputs

Determine from the user message or ask once:

- **`<project>`** — project slug under `projects/` (e.g. `lz`, `ovnet`). Default to the project mentioned in chat or the one whose connection file is open.

## Python environment

From repo root, use `.venv/bin/python` when `.venv/` exists. If dependencies are missing (`httpx`, …), create the venv and install:

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Use `PYTHON=python` only when system Python already has requirements installed.

## Step 1 — Access rights (verbatim)

`POST {xeeloUrl}/graphql` with Bearer token. Use this query **verbatim**:

```graphql
query ExampleQuery {
  health
  access_rights {
    id
    code
    name
    canRead
    canWrite
    canDelete
  }
}
```

## Step 2 — Introspection + save

Overwrite on every `/graphql` (same idea as a DB snapshot). Create `projects/<project>/graphql/` if missing.

- `projects/<project>/graphql/access_rights.json` — `ExampleQuery` result
- `projects/<project>/graphql/schema.json` — `__schema` from full introspection

Do **not** paste the schema JSON into chat (~1.8 MB). Read from disk / `__type` for the current task.

`/new-project` does not create `graphql/`. Nested `projects/` gitignores these JSON files (`templates/projects-repo/.gitignore`); copy that ignore into an existing sites repo if it is missing.

From repo root:

```bash
$PYTHON - <<'PY'
from pathlib import Path
import json
from scripts.ot_builder.graphql_client import ConnectionConfig, XeeloGraphqlClient

PROJECT = "projects/<project>"
EXAMPLE = """
query ExampleQuery {
  health
  access_rights {
    id
    code
    name
    canRead
    canWrite
    canDelete
  }
}
"""
INTROSPECTION = """
query FullIntrospection {
  __schema {
    queryType { name }
    mutationType { name }
    subscriptionType { name }
    types {
      kind
      name
      description
      fields(includeDeprecated: true) {
        name
        description
        args {
          name
          description
          type { kind name ofType { kind name ofType { kind name ofType { kind name } } } }
          defaultValue
        }
        type { kind name ofType { kind name ofType { kind name ofType { kind name } } } }
        isDeprecated
        deprecationReason
      }
      inputFields {
        name
        description
        type { kind name ofType { kind name ofType { kind name ofType { kind name } } } }
        defaultValue
      }
      interfaces { kind name }
      enumValues(includeDeprecated: true) { name description isDeprecated deprecationReason }
      possibleTypes { kind name }
    }
    directives {
      name
      description
      locations
      args {
        name
        description
        type { kind name ofType { kind name ofType { kind name } } }
        defaultValue
      }
    }
  }
}
"""

cfg = ConnectionConfig.load(Path(PROJECT) / ".xeelo-connection.json")
out = Path(PROJECT) / "graphql"
out.mkdir(parents=True, exist_ok=True)
with XeeloGraphqlClient(cfg) as client:
    rights = client.request(EXAMPLE)
    schema = client.request(INTROSPECTION)
(out / "access_rights.json").write_text(json.dumps(rights, indent=2) + "\n", encoding="utf-8")
(out / "schema.json").write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
types = (schema.get("__schema") or {}).get("types") or []
print("health", rights.get("health"))
print("access_rights", len(rights.get("access_rights") or []))
print("schema_types", len(types))
print("wrote", out / "access_rights.json", (out / "access_rights.json").stat().st_size)
print("wrote", out / "schema.json", (out / "schema.json").stat().st_size)
PY
```

Replace `<project>` before running.

## Step 3 — Query with rights + schema

After a successful save:

1. **`Select_`** only when `access_rights` has `canRead` for that object `code`.
2. **`Mutate_`** only when `canWrite`.
3. **`Delete_request`** only when `canDelete`. `code` is the GraphQL object code (`Select_{code}`).
4. Argument and filter shapes (`created`, `dateFrom` / `dateTo`, `lineFilters`, …) come from **`schema.json`** (or a follow-up `__type` query). Do not invent them from product source. Do not add them to `docs/entities/graphql.md` unless the user asks to update the KB.
5. Pagination: `limit` default 1000, max 10000, `offset`.

Use `XeeloGraphqlClient.request` for the user’s query after this refresh.

## Output

Report:

1. `health`
2. `access_rights` count (and which objects are readable / writable / deletable if relevant)
3. Paths and byte sizes of `graphql/schema.json` and `graphql/access_rights.json`
4. Then answer the user’s GraphQL question using those files

## Errors

- **Auth / ACCESS_DENIED** — token lacks GraphQL access. Ask the user to put a valid token in `.xeelo-connection.json`. There is no refresh.
- **Introspection disabled** — `GRAPHQL_INTROSPECTION=false` on the site; stop and say schema cannot be loaded.
- **Timeout** — large schema; retry with a longer client timeout if needed.
