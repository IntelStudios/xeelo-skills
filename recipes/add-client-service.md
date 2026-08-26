# Recipe: Add Client-Service (External service)

Fill a field from an **Object Service** of type **External service** when another field changes (IČO → company name, DIČ → VIES valid, …).

Not a field type — ObjectService is a site catalog. Client-Service is a **template-line** calculation (`type: service`).

## When to use

Task mentions: ARES, VIES, VAT payer, IČO lookup, fill name from register, call an HTTP service from the form.

## Spec

One ObjectService row **per target field**. Same `{@1}` source, different `&field=`.

```yaml
# spec/object-services.yaml
objectServices:
  ares_name:
    name: ARES Name
    type: external
    link: "https://<ares-host>/api/parse?query={@1}&field=Name"
  ares_dic:
    name: ARES DIC
    type: external
    link: "https://<ares-host>/api/parse?query={@1}&field=DIC"

# layout
- name: ICO
  code: ICO
  type: text
  slot: 1
  width: 50
  order: 1
- name: Company name
  code: COMPANY_NAME
  type: text
  slot: 2
  width: 50
  order: 2
- name: VAT ID
  code: DIC
  type: text
  slot: 3
  width: 50
  order: 3

# spec/templates.yaml
templates:
  - key: default
    name: Default
    isDefault: true
    fields:
      COMPANY_NAME:
        clientCalculation:
          type: service
          service: ares_name
          expr: "id{ICO}"
      DIC:
        clientCalculation:
          type: service
          service: ares_dic
          expr: "id{ICO}"
```

Put the real host in `link`. `{@1}` stays literal. `expr` `id{CODE}` compiles to the line id.

Combo source: `id{CODE}` = stored value, `id{CODE}r` = display name. Extra params: `id{ICO}, 'CZ'`.

## Tables to emit

1. **ObjectService** (once per `objectServices:` key) — `ObjectServiceTypeID = 1`, `ObjectServiceLink`
2. **ObjectDefaultLine** — `ObjectDefaultLineClientCalculationTypeID = 3`, compiled `expr`, `ObjectServiceID`
3. Edge: `ObjectDefaultLine → ObjectService`

Same bind on **subgrid** columns (`ObjectSubDefaultLine`). Service type filter is **1–2** (same as non-report request lines).

## Hints

- Type 1 is a **browser GET**. The host needs CORS. `ObjectServiceHeader` is not sent.
- Response must be `{ "Result": "…" }` (or an array with `Result`). See the External service contract in [object-services.md](../docs/entities/object-services.md#contract-for-a-new-external-service).
- Known wrappers: ARES, VIES, Vatpayer — field names in that doc.
- Report-line Client-Service (types 3–6) is **not** in spec.

Details: [object-services.md](../docs/entities/object-services.md). Grammar: [xeelo-grammar.md](../docs/entities/xeelo-grammar.md#client-service).
