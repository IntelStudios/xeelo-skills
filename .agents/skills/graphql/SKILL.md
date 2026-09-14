---
name: graphql
description: >-
  Use verified site GraphQL schema and current access_rights from
  POST {xeeloUrl}/graphql, with targeted or full discovery as needed. Use when the user wants to
  query or mutate GraphQL, run Select_ / Mutate_, count tickets, filter headers
  (created / createdDate), inspect access_rights, or invokes /graphql. Not for
  admin transfer (/download-db, /publish, /precompile).
disable-model-invocation: true
---

# GraphQL (live schema + access_rights)

When the user wants to use site GraphQL (`Select_` / `Mutate_`, ticket counts, header filters, `access_rights`), **read this skill first**. Verify schema provenance from this endpoint and load current rights from `POST {xeeloUrl}/graphql` — do not guess filter shapes from product source. Admin transfer stays `/download-db`, `/publish`, `/precompile`.

GET `{xeeloUrl}/graphql` is Apollo Sandbox (HTML). Schema comes from **POST** introspection.

## Prerequisites

- `projects/<project>/.xeelo-connection.json` exists and is filled in:
  - `xeeloUrl` — Xeelo site URL (User UI)
  - `token` — GraphQL Bearer token (`isAdmin` for transfer/precompile; any GraphQL token for `access_rights` / `Select_`)
  - `permission` — missing/empty = `read-only`. **`Select_`** (and this skill’s schema / `access_rights` load) is allowed at every level. **`Mutate_` / `Delete_`** need `read-write` or `full`.
- If the connection file is missing or `xeeloUrl` / `token` is empty, stop and tell the user to complete it first (see `/new-project` checklist).

## Inputs

Determine from the user message or ask once:

- **`<project>`** — project slug under `projects/`. Default to the project mentioned in chat or the one whose connection file is open.

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

## Step 2 — Choose schema discovery scope

Keep Step 1's live access-rights check for the current connection; cached schema never grants access. Re-read connection permission before a mutation.

- **Routine query:** reuse schema verified for this exact endpoint when provenance and continued relevance are known. Record endpoint, capture time and available configuration revision in local project notes without credentials. A matching folder name or recent timestamp alone does not establish freshness.
- **Known missing type details:** use targeted `__type(name: ...)`, following required input/return types and checking argument wrappers and enum values. Do not guess types. Keep partial introspection separate from complete `schema.json`.
- **First setup without adequate schema, explicit full refresh or broad schema change:** use the full refresh below. A missing or changed type may need only targeted discovery. After a relevant deployment/precompile, endpoint change or schema-validation error, invalidate affected assumptions and verify again before business operations.
- **Unknown provenance or disabled introspection:** use supplied schema only when verified for this target and applicable to the request; otherwise stop the dependent query and explain what is missing. Never borrow another site's schema.

Create `projects/<project>/graphql/` if missing. Save current rights on every invocation. Replace complete schema only after successful full refresh; a failed refresh must not make the previous schema appear current.

### Full refresh example

- `projects/<project>/graphql/access_rights.json` — `ExampleQuery` result
- `projects/<project>/graphql/schema.json` — `__schema` from full introspection

Do **not** paste the schema JSON into chat (~1.8 MB). Read from disk / `__type` for the current task.

`/new-project` does not create `graphql/`. Nested `projects/` gitignores these JSON files (`templates/projects-repo/.gitignore`); copy that ignore into an existing sites repo if it is missing.

Run this combined example only when full refresh was selected (it includes Step 1; do not repeat that rights request separately). For routine reuse, execute only Step 1 and save its result.

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

After current rights and sufficient target-specific schema have been verified:

1. **`Select_`** only when `access_rights` has `canRead` for that object `code`. Allowed at **`read-only`**, `read-write`, and `full`.
2. **`Mutate_`** only when `canWrite` **and** connection `permission` is `read-write` or `full`. In `read-only`, stop and tell the user to set `permission`.
3. **`Delete_request`** only when `canDelete` **and** `permission` is `read-write` or `full`. `code` is the GraphQL object code (`Select_{code}`).
4. Argument and filter shapes (`created`, `dateFrom` / `dateTo`, `lineFilters`, …) come from **`schema.json`** (or a follow-up `__type` query). Do not invent them from product source. Do not add them to `docs/entities/graphql.md` unless the user asks to update the KB.
5. Pagination: platform `limit` default 1000, max 10000, `offset`. For an initial diagnostic Select explicitly request a small page (for example 10 rows), only needed fields and a schema-verified filter where appropriate. Fetch further pages sequentially only as needed; do not rely on the platform default.
6. Bound nested collections using arguments actually supported by the verified schema. For broader retrieval agree row/page and response-size budgets. Stop further pages and narrow the query if a response is unexpectedly large or the budget is exhausted. These are agent-side limits; do not claim the existing client enforces a streaming byte cap.
7. For counts or existence checks prefer a verified dedicated field when available; otherwise state the limits of a bounded result instead of retrieving all records or presenting a partial page as the total.

Use `XeeloGraphqlClient.request` after these checks; a full refresh is not required for every query.

## Output

Report:

1. `health`
2. `access_rights` count (and which objects are readable / writable / deletable if relevant)
3. Schema source (reused, targeted or full), provenance, and paths/byte sizes of artifacts actually saved
4. Answer the question and state pagination, truncation or unresolved schema limits; do not claim a full refresh if none ran

## Errors

- **Auth / ACCESS_DENIED** — token lacks GraphQL access. Ask the user to put a valid token in `.xeelo-connection.json`. There is no refresh.
- **Permission** — `Mutate_` / `Delete_` in `read-only`: stop; user must set `permission` to `read-write` or `full`. Do not change the field unless they ask.
- **Introspection disabled** — apply the verified supplied-schema rule in Step 2 or stop the dependent query.
- **Timeout** — narrow discovery or the read query before considering a longer timeout. A mutation timeout is an unknown outcome: reconcile through authorized reads before any retry; never repeat a write merely with a longer timeout.
