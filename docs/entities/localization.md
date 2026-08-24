# Metadata localization (LanguageTable)

Admin can translate **display names** of objects, tabs, sections, fields, and related entities into the site’s user languages. Canonical text stays on the entity column (`ObjectLineName`, `ObjectName`, …). Translations are extra rows in **`LanguageTable`**.

This is **not** Admin/User chrome i18n (UI shell strings). Those JSON packs are product UI, not object metadata.

Schema: [`data/schemas/LanguageTable.json`](../data/schemas/LanguageTable.json) · languages: [`data/enums/UserLanguage.json`](../data/enums/UserLanguage.json) · spec: [`spec/language-table.yaml`](../transfer/spec-format.md#localization-speclanguage-tableyaml)

## How it is stored

| Piece | Where |
|-------|--------|
| Default label | Entity column (`ObjectLineName`, `ObjectLineTabName`, …) |
| Translation | `LanguageTable`: `(TableName, ColumnName, RowID, UserLanguageCode)` → `LanguageTableData` |
| Unique key | Those four columns (plus `IsActive`) |

`RowID` is the parent entity PK as a string. Empty / inactive translation → runtime **falls back** to the default column.

User GUI reads translated labels from **PreCompile** cache (language XML baked into settings). After an Object Transfer that changes `LanguageTable`, run **/publish**. If the transfer is already applied, `/precompile` is enough.

## Languages

Seed `UserLanguage` codes (15):

`en` `cs` `de` `pl` `sk` `hu` `nl` `sl` `hr` `fr` `es` `pt` `ro` `zh-cn` `zh-tw`

Admin translation modal lists every **active** row. Do not write `en` into `languageTable` unless it must differ from the canonical `name` (unusual).

## Admin UI

- Globe icon on fields marked translatable (object name, line name, on-grid name, template name, role, status, workflow name, step **action** name, object/update action name, company, object type, …).
- Tabs and sections: globe on the tab/section header (same `LanguageTable` mechanism).
- **Label translation** portlet: bulk grid / Excel / machine translate for the object subtree.

`WorkflowStepName` (the step itself) is **not** translatable — only `WorkflowStepActionName` and `WorkflowStepSuccessMessage`.

HTML/memo columns (template hint, description memo, button message, object messages) use the same table. Object-message **names** and **HTML** are in `languageTable.objectMessages` ([object-messages.md](object-messages.md)). Template field **hints** are in `languageTable.templateHints` (`ObjectDefaultLineHint`; RowID is `ObjectDefaultLineID`, not `ObjectLineID`). Description memo and button message are not in `language-table.yaml` yet.

## Spec: `spec/language-table.yaml`

Canonical `name` in `object.yaml` stays **English**. Translations live in a separate fragment, keyed by **entity type** then **entity key** then **language**:

```yaml
languageTable:
  object:
    cs: Účet
  tabs:
    General:
      cs: Obecné
  sections:
    General/Details:
      cs: Podrobnosti
  lines:
    ACCOUNT_NUMBER:
      cs: Číslo účtu
      # onGrid:
      #   cs: Č. účtu    # only when the site wants inbox headers translated
  roles:
    requestor:
      cs: Žadatel
  statuses:
    draft:
      cs: Návrh
  workflow:
    cs: Account
  stepActions:
    Draft/Submit:
      cs: Odeslat
  templateHints:
    default:
      ACCOUNT_NUMBER:
        cs: Zadejte IBAN bez mezer
```

| Spec key | Maps to |
|----------|---------|
| `object` | `Object.ObjectName` |
| `company` | `Company.CompanyName` |
| `objectType` | `ObjectType.ObjectTypeName` |
| `tabs.<TabName>` | `ObjectLineTabName` (key = canonical tab `name`) |
| `sections.<TabName>/<SectionName>` | `ObjectSectionName` |
| `lines.<code>` | `ObjectLineName` |
| `lines.<code>.onGrid` | `ObjectLineOnGridName` |
| `templates.<key>` | `ObjectDefaultName` |
| `roles.<key>` / `statuses.<key>` | `RoleName` / `RequestStatusName` |
| `workflow` | `WorkflowName` |
| `stepActions.<stepName>/<actionName>` | `WorkflowStepActionName` |
| `objectActions.<key>` / `updateActions.<key>` | action display names |
| `periodics.<key>` | `PeriodicName` |
| `periodicActions.<periodicKey>/<actionKey>` | `PeriodicActionName` |
| `schedulers.<periodicKey>` | `SchedulerName` (when `periodics[].cron` is set) |
| `objectMessages.<key>` | `ObjectMessageName` |
| `objectMessages.<key>.html` | HTML body — LanguageTable ColumnName `ObjectMessageFormat` (DB column is `ObjectMessageFromat`) |
| `templateHints.<templateKey>.<code>` | `ObjectDefaultLineHint` — canonical English stays on `templates.fields.<code>.hint`; RowID is the template-line PK |

Generator emits `LanguageTable` rows (`IsActive=1`) and ObjectSetup edges `Parent → LanguageTable`. Extract writes the fragment only when translations exist.

Site-specific “always Czech / onGrid stays English” rules: [`projects/<name>/conventions.md`](../projects.md) — not this doc.

## Object Transfer

`LanguageTable` is a child of whichever entity owns the label. Import as New remaps `RowID` to the new parent PK. Generator defaults Orig. ID like other tables.

## Related

- **LanguageVocab** — product vocabulary (home page names, …), not object spec.
- User’s language preference is on the user record (not in DB/Object transfer).
