# Xeelo Grammar (validation + client calc)

One grammar for template **extended validation** and **client calculations**. Roots differ by prefix. Stored expressions **do not include** the prefix — Admin and runtime prepend it at compile time.

Line types and which calc/validation Admin allows: [object-line-types.md](object-line-types.md). Spec compile of `id{FIELD}`: [spec-format.md](../transfer/spec-format.md#templates-spectemplatesyaml).

```text
start: (validation | calculation) EOF
validation: 'v#' condition
calculation: string | math | …
math: '1#' (mathExpr | mathIf)
string: '2#' (stringExpr | stringIf | getMemo | getSubMemo)
```

| Use | Prefix | G4 root | Who prepends |
|-----|--------|---------|--------------|
| Extended hidden / disabled / mandatory | `v#` | `condition` | `validation.ts`, Admin `grammarValidation()` |
| Client-Math | `1#` | `math` | `client-calculation.ts`, Admin `grammarCalculationValidation()` |
| Client-String | `2#` | `string` | same |
| Client-Service | `3#` | `service` | same — [object-services.md](object-services.md#client-service) |
| Client-UserInfo | `7#` | `userInfo` | same |
| Client-DeviceInfo | `8#` | `deviceInfo` | same |

## Line refs and literals

| Token | Meaning |
|-------|---------|
| `id123` | Line value (`ObjectLineID`) |
| `id123r` | Combo **Name** (display) |
| `id123m` | Memo-style accessor |
| `'text'` | STRING — **single quotes** only (escape `\` and `'`) |

In spec, write `id{FIELD_CODE}`; generator replaces with `id{ObjectLineID}` (request template) or `id{ObjectSubLineID}` (subgrid `clientCalculation`). Reference binds: `{referenceKey.valueKey}` → `ObjectLineSourceValueBind` (numeric unquoted; else `'bind'`).

## Condition (extended validation and `if`)

Used by `v#` and by `if (…) then (…) else (…)` in Math/String.

**Precedence:** `condition` is `orCondition` **AND** `orCondition`…; each `orCondition` is `anyCondition` **OR** `anyCondition`…. So **AND is outer**: `A and B or C` = `A AND (B OR C)`. Use `()`.

### Math branch

`mathExpr mathOperator mathExpr` with `=` `!=` `>` `>=` `<` `<=`. Both sides use **Client-Math** evaluation (numbers).

### String branch

- `true` / `yes` → true (`hidden: true` in spec)
- Unary on `lineId`: `isempty`, `isnotempty`, `ischecked`, `isnotchecked` — `ischecked` when the value is `'1'` or `'true'`
- Binary: `stringExpr` `=` `!=` `like` `not like` `contains` — both sides **Client-String** (concat, `substring`)

## Extended validation

`ObjectDefaultLineValidationID = 9`. Three **independent** booleans; empty string = do not apply that axis.

| Spec | Column | Runtime if true |
|------|--------|-----------------|
| `extended.hidden` | `ObjectDefaultLineValidationExtHiddenCondition` | hide |
| `extended.disabled` | `ObjectDefaultLineValidationExtDisabledCondition` | disable |
| `extended.mandatory` | `ObjectDefaultLineValidationExtMandatoryCondition` | required |

Stored **without** `v#`. Examples:

```text
id{TYPE} != {account_type.FIO}
id{NAME} isempty
id{FLAG} ischecked
substring(id{CODE}, 1, 1) = 'I' and 10 * 10 > 99
true
```

Which Ext\* axes Admin enables depends on line type — [object-line-types.md](object-line-types.md#validation).

## Client-Math vs Client-String

Same grammar file; different roots and how `+` runs.

| | Client-Math (`1#`) | Client-String (`2#`) |
|--|--------------------|----------------------|
| Root | `mathExpr` or `mathIf` | `stringExpr`, `stringIf`, `getMemo`, `getSubMemo` |
| `+` | numeric add (`toFixed` precision) | concatenation |
| Operands | INT, DECIMAL, `lineId` via **numberValue** (`NaN` → `0`) | `'…'`, `lineId` via **stringValue** (null → `''`), `substring(id, from, len)` (**1-based** `from`), `true`/`false` → `'1'`/`'0'` |
| `*` `/` `-` | yes | no |
| `if` body | `mathExpr` | `stringExpr` |
| Result written to the line | `String(number)` | string |
| Extra | — | `getmemo(idN)` deprecated; use `idN` |

Spec `templates.fields.<code>.clientCalculation`:

```yaml
clientCalculation:
  type: math    # or string
  expr: "id{QTY} * id{PRICE}"
```

Generator writes `ObjectDefaultLineClientCalculationTypeID` + compiled `expr` **without** `1#`/`2#`.

Examples (stored `expr`):

```text
(2 + id{QTY}) * (10 / id{QTY}) + 5
if (id{QTY} > 4) then (666) else (0)
id{NAME} + ' ' + substring(id{NAME}, 1, 1)
if (id{TYPE} = 'FIO' and id{TYPE} isnotempty) then ('1') else ('0')
```

## Client-Service

G4 prefix `3#`. Spec `type: service` stores `expr` **without** `3#`. Params are comma-separated `id{CODE}` / STRING; `{@n}` in the ObjectService URL is filled at runtime. Bind `clientCalculation.service` to `spec/object-services.yaml`. The source field's `valueChanges` debounce is **400 ms**; `calcDelay` / `calcConfirm` on that source are opt-in — [object-line-types.md](object-line-types.md#client-calc-delay-and-confirm). Details: [object-services.md](object-services.md#client-service).

```yaml
clientCalculation:
  type: service
  service: ares_name
  expr: "id{ICO}"
```

DateAdd, DateDiff, and Focus share G4 prefixes `4#`–`6#` but are not specified here — see the type matrix in [object-line-types.md](object-line-types.md#client-calculations).

## Client-UserInfo / Client-DeviceInfo

Text lines only (`ObjectLineTypeID` 3). G4 root is a single `placeholderParam` (`{…}`). Stored in `ObjectDefaultLineClientCalculation` **without** `7#` / `8#`. Empty `expr` is invalid (`7# ''` does not parse).

```yaml
clientCalculation:
  type: user_info    # or device_info
  expr: "{UserName}"
```

Unknown placeholders resolve to `''`. Matching for DeviceInfo is **case-insensitive**.

### UserInfo placeholders (`type: user_info`)

Resolved server-side for the current user.

| `expr` | Result |
|--------|--------|
| `{UserLogin}` | login |
| `{UserName}` | display name |
| `{UserID}` | user ID |
| `{UserLanguage}` | language code |
| `{UserInfo01}` … `{UserInfo09}` | `User.UserData01` … `UserData09` |

`{UserInfo10}` is not a data column; it returns `''`.

### DeviceInfo placeholders (`type: device_info`)

| `expr` | Web GUI | Mobile |
|--------|---------|--------|
| `{DeviceType}` | `'User'` (client) | `'Mobile'` (client) |
| `{DeviceLocation}` | geolocation (client) | geolocation (client) |
| `{DeviceIP}` | client IP (API) | client IP (API) |
| `{DeviceID}` | `''` | device ID (API) |
| other | `''` | `''` |
