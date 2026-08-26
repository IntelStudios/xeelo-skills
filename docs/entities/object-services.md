# Object Service and Client-Service

Site catalog of HTTP (or SQL) endpoints that a **template line** can call from a **Client-Service** calculation. The service is not a field type.

**Tables:** `ObjectService` (catalog), `ObjectDefaultLine.ObjectServiceID` / `ObjectSubDefaultLine.ObjectServiceID` (bind).

Catalog: [`ObjectServiceType.json`](../enums/ObjectServiceType.json). Recipe: [`add-client-service.md`](../../recipes/add-client-service.md). Spec: [`spec/object-services.yaml`](../transfer/spec-format.md#object-services-specobject-servicesyaml). Grammar: [xeelo-grammar.md](xeelo-grammar.md#client-service).

## ObjectService

| Column | Role |
|--------|------|
| `ObjectServiceName` | Display name |
| `ObjectServiceTypeID` | 1–6 (seed `ObjectServiceType`, **not transferred**) |
| `ObjectServiceLink` | URL template for types **1** and **3–6** |
| `ObjectServiceHeader` | Extra HTTP headers for types **3–6** only (`name:value\|name2:value2`) |
| `ObjectServiceSQL` | T-SQL for type **2** |
| `IsActive` | Soft disable |

This KB generates **type 1 External service** only.

### Types

| ID | Name | Link | Header | SQL | Who calls |
|----|------|------|--------|-----|-----------|
| **1** | External service | required | unused | unused | **Browser GET** to the substituted URL |
| 2 | Internal SQL | unused | unused | required | Xeelo `POST …/Execute` → `@1`…`@10` |
| 3 | External report | required | used | unused | Xeelo server GET proxy |
| 4 | External calendar | required | used | unused | same |
| 5 | External bar chart | required | used | unused | same |
| 6 | External pie chart | required | used | unused | same |

Types 2–6 are not in spec. After generate, patch OT JSON if you need them (same pattern as [server calculations](object-line-types.md#server-calculations)).

Admin **Service** dropdown on Client-Service:

| Line | Services offered |
|------|------------------|
| Report (13) | types **3–6** |
| Any other request line | types **1–2** |
| Subgrid column | **same filter** (no report type on subgrid → **1–2**). Admin’s subgrid editor currently lists all types — treat that as an Admin bug, not a platform rule. |

## Client-Service

Client calculation type **3**, spec `clientCalculation.type: service`. Requires an `ObjectService` bind.

```yaml
clientCalculation:
  type: service
  service: ares_name          # key in spec/object-services.yaml
  expr: "id{ICO}"             # params for {@1}, {@2}, … — stored without 3#
```

`expr` is a comma-separated list of `serviceParam`: `id{CODE}`, `id{CODE}r` (combo **display** name; plain `id{CODE}` is the stored value), `id{CODE}m` on a subgrid (parent request line), or a STRING literal `'…'`. Generator compiles `id{CODE}` to `id{ObjectLineID}` (or `ObjectSubLineID` on a subgrid).

`ObjectServiceLink` placeholders are **`{@1}`**, `{@2}`, … (1-based, same order as `expr`). They are **not** compiled at generate time.

Trigger: source field `valueChanges`, default debounce **400 ms** (not blur). `ObjectDefaultLineIsClientCalcConfirm` shows a Refresh button on text/number — not a modal; not in spec yet.

On form load, Client-Service does **not** run until a dependency changes (external report lines are the exception; those types are not in spec).

### Type 1 runtime

1. Substitute `{@n}` in `ObjectServiceLink`.
2. Browser **GET** that URL (CORS must allow the Xeelo origin).
3. Read JSON `{ "Result": "…" }` or `[{ "Result": "…" }]` and write `Result` onto **this** line.
4. HTTP/network failure → field cleared (`null`).

**`ObjectServiceHeader` is not sent** for type 1 (Admin disables it). A Bearer token on the catalog service does not reach the browser call. The host must allow an unauthenticated GET (or a wrapper that does not need a header from the form).

One Client-Service fills **one** line. A full object in `Result` is a poor fit for a text field. Typical pattern: one `ObjectService` row per target field, same `{@1}`, different `&field=PropertyName`.

## Contract for a new External service

Anything the form should call as type 1 must implement this. The ARES/VIES/Vatpayer wrappers follow it; a custom host can use other paths as long as GET + `Result` hold.

| Rule | Detail |
|------|--------|
| Method | **GET** |
| URL | Reachable from the user’s browser (**CORS**) |
| Params | Query (or path) filled from `{@1}`…`{@n}` in `ObjectServiceLink` |
| Success body | JSON `{ "Result": "<string>" }` or `[{ "Result": "<string>" }]` |
| Optional `field=` | If the backend can return a larger object, `?field=Name` should put that property in `Result` as a **string** |
| Auth | Type 1 sends **no** custom headers. Do not require `Authorization` from the form |
| Empty / not found | HTTP 200 with empty `Result` (or the client clears the field on error) |

Suggested shape (used by the known wrappers):

```text
GET /api/parse?query={@1}
GET /api/parse?query={@1}&field=Name
```

Without `field`, `Result` may be an object. Prefer `field=` when filling Xeelo lines.

Do **not** use POST, a non-`Result` envelope, or report/chart JSON — those are other ObjectService types (server-proxied).

## Known services

Not Xeelo seed. Deploy the wrapper, put its **host** in `objectServices.*.link`. Paths and `field=` names below are the contract.

### ARES (Czech business register)

`{@1}` = IČO.

```text
/api/parse?query={@1}
/api/parse?query={@1}&field=Name
```

| `field=` | Meaning |
|----------|---------|
| `ICO` | IČO |
| `DIC` | DIČ |
| `Name` | Subject name |
| `RegistrationDate` | Registration date |
| `Type` | Legal form |
| `FullStreet` | Street + numbers |
| `FullCity` | Postcode + city |
| `Country` | Country |
| `City` | City |
| `City2` | City part |
| `City3` | District |
| `PostCode` | Postcode |
| `Street` | Street |
| `StreetNumber` | Descriptive number |
| `StreetNumber2` | Orientation number |
| `TradeLicenseIssuer` | Trade licence issuer |
| `RegisterLocation` | Court / register |
| `RegisterNumber` | File number |
| `Nace` | NACE codes (`\|`-joined) |

### VIES (EU VAT)

`{@1}` = full VAT ID including country prefix (e.g. `CZ12345678`). Length &lt; 3 → `valid` is `false`.

```text
/api/parse?query={@1}
/api/parse?query={@1}&field=valid
```

| `field=` | Meaning |
|----------|---------|
| `valid` | `true` / `false` (string) |
| `name` | Name from VIES |
| `address` | Address (newlines folded to `, `) |

### Vatpayer (Czech unreliable VAT payer)

`{@1}` = DIČ. Requires `type=status` or `type=detail`.

```text
/api/parse?query={@1}&type=status&field=unreliablePayer
/api/parse?query={@1}&type=detail&field=subjectName
```

**`type=status`**

| `field=` | Meaning |
|----------|---------|
| `unreliablePayer` | `ANO` / `NE` |

**`type=detail`**

| `field=` | Meaning |
|----------|---------|
| `unreliablePayer` | `ANO` / `NE` |
| `subjectName` | Name |
| `street` | Street |
| `cityPart` | City part |
| `city` | City |
| `postalCode` | Postcode |
| `country` | Country |
| `lastAccountPrefix` | Last published account prefix |
| `lastAccountNumber` | Account number |
| `lastAccountBank` | Bank code |
| `accounts` | JSON array of published accounts (not a simple line fill) |

## Transfer

`ObjectService` is type **U**. Edges: `ObjectDefaultLine → ObjectService`, `ObjectSubDefaultLine → ObjectService`. `ObjectServiceType` is site seed, not transferred.

Generator emits only **used** type-1 rows referenced by `clientCalculation.service`.
