"""Emit and extract LanguageTable rows from spec languageTable maps."""

from __future__ import annotations

from typing import Any

from ot_builder.ids import IdRegistry

USER_LANGUAGE_CODES = (
    "en",
    "cs",
    "de",
    "pl",
    "sk",
    "hu",
    "nl",
    "sl",
    "hr",
    "fr",
    "es",
    "pt",
    "ro",
    "zh-cn",
    "zh-tw",
)

# spec languageTable key → (SQL table, name column, IdRegistry scalar or category)
SCALAR_TARGETS: dict[str, tuple[str, str, str]] = {
    "object": ("Object", "ObjectName", "objectId"),
    "company": ("Company", "CompanyName", "companyId"),
    "objectType": ("ObjectType", "ObjectTypeName", "objectTypeId"),
    "workflow": ("Workflow", "WorkflowName", "workflowId"),
}

CATEGORY_TARGETS: dict[str, tuple[str, str, str]] = {
    "tabs": ("ObjectLineTab", "ObjectLineTabName", "tabs"),
    "sections": ("ObjectLineSection", "ObjectSectionName", "sections"),
    "templates": ("ObjectDefault", "ObjectDefaultName", "templates"),
    "roles": ("Role", "RoleName", "roles"),
    "statuses": ("RequestStatus", "RequestStatusName", "statuses"),
    "objectActions": ("ObjectAction", "ObjectActionName", "objectActions"),
    "updateActions": ("ObjectUpdateAction", "ObjectUpdateActionName", "updateActions"),
}

KNOWN_TYPES = frozenset(
    {*SCALAR_TARGETS, *CATEGORY_TARGETS, "lines", "stepActions"}
)


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _boolish(val: Any) -> bool:
    return str(val) in ("1", "True", "true")


def _lang_map(entry: Any) -> dict[str, str]:
    if not isinstance(entry, dict):
        return {}
    out: dict[str, str] = {}
    for code, text in entry.items():
        if code == "onGrid":
            continue
        if not isinstance(text, str):
            continue
        stripped = text.strip()
        if stripped:
            out[str(code)] = stripped
    return out


def language_table_id_key(table: str, column: str, entity_key: str, lang: str) -> str:
    return f"{table}:{column}:{entity_key}:{lang}"


def _emit_langs(
    result: Any,
    registry: IdRegistry,
    *,
    parent_table: str,
    parent_id: int,
    column: str,
    entity_key: str,
    langs: dict[str, str],
) -> None:
    for lang, text in langs.items():
        composite = language_table_id_key(parent_table, column, entity_key, lang)
        lt_id = registry.require("languageTables", composite)
        result.rows.setdefault("LanguageTable", []).append(
            {
                "LanguageTableID": lt_id,
                "TableName": parent_table,
                "ColumnName": column,
                "RowID": str(parent_id),
                "UserLanguageCode": lang,
                "LanguageTableData": text,
                "IsActive": 1,
            }
        )
        result.edges.append(
            {
                "TableName": parent_table,
                "TableRowID": parent_id,
                "ChildTableName": "LanguageTable",
                "ChildTableRowID": lt_id,
            }
        )


def _require_parent(registry: IdRegistry, category: str, key: str, *, kind: str) -> int:
    parent_id = registry.get(category, key)
    if parent_id is None:
        raise ValueError(f"languageTable.{kind}: unknown key {key!r}")
    return parent_id


def _require_scalar(registry: IdRegistry, scalar: str, *, kind: str) -> int:
    parent_id = registry.get_scalar(scalar)
    if parent_id is None:
        raise ValueError(f"languageTable.{kind}: parent {scalar} is not allocated")
    return parent_id


def _step_action_id(registry: IdRegistry, key: str) -> int:
    parent_id = registry.get("workflowStepActions", key)
    if parent_id is not None:
        return parent_id
    if "/" in key:
        action_name = key.split("/", 1)[1]
        parent_id = registry.get("workflowStepActions", action_name)
        if parent_id is not None:
            return parent_id
    raise ValueError(f"languageTable.stepActions: unknown key {key!r}")


def emit_language_table(spec: dict, registry: IdRegistry, result: Any) -> None:
    payload = spec.get("languageTable") or {}
    if not payload:
        return
    if not isinstance(payload, dict):
        raise ValueError("languageTable must be a mapping")

    for kind, body in payload.items():
        if kind not in KNOWN_TYPES:
            raise ValueError(f"languageTable: unknown type {kind!r}")
        if kind in SCALAR_TARGETS:
            table, column, scalar = SCALAR_TARGETS[kind]
            langs = _lang_map(body)
            if not langs:
                continue
            parent_id = _require_scalar(registry, scalar, kind=kind)
            _emit_langs(
                result,
                registry,
                parent_table=table,
                parent_id=parent_id,
                column=column,
                entity_key=kind,
                langs=langs,
            )
            continue
        if kind == "lines":
            if not isinstance(body, dict):
                raise ValueError("languageTable.lines must be a mapping")
            for code, entry in body.items():
                if not isinstance(entry, dict):
                    raise ValueError(f"languageTable.lines.{code}: expected mapping")
                parent_id = _require_parent(registry, "fields", str(code), kind="lines")
                langs = _lang_map(entry)
                if langs:
                    _emit_langs(
                        result,
                        registry,
                        parent_table="ObjectLine",
                        parent_id=parent_id,
                        column="ObjectLineName",
                        entity_key=str(code),
                        langs=langs,
                    )
                on_grid = entry.get("onGrid")
                grid_langs = _lang_map(on_grid) if isinstance(on_grid, dict) else {}
                if grid_langs:
                    _emit_langs(
                        result,
                        registry,
                        parent_table="ObjectLine",
                        parent_id=parent_id,
                        column="ObjectLineOnGridName",
                        entity_key=str(code),
                        langs=grid_langs,
                    )
            continue
        if kind == "stepActions":
            if not isinstance(body, dict):
                raise ValueError("languageTable.stepActions must be a mapping")
            for key, entry in body.items():
                langs = _lang_map(entry)
                if not langs:
                    continue
                parent_id = _step_action_id(registry, str(key))
                _emit_langs(
                    result,
                    registry,
                    parent_table="WorkflowStepAction",
                    parent_id=parent_id,
                    column="WorkflowStepActionName",
                    entity_key=str(key),
                    langs=langs,
                )
            continue
        table, column, category = CATEGORY_TARGETS[kind]
        if not isinstance(body, dict):
            raise ValueError(f"languageTable.{kind} must be a mapping")
        for key, entry in body.items():
            langs = _lang_map(entry)
            if not langs:
                continue
            parent_id = _require_parent(registry, category, str(key), kind=kind)
            _emit_langs(
                result,
                registry,
                parent_table=table,
                parent_id=parent_id,
                column=column,
                entity_key=str(key),
                langs=langs,
            )


def _rev(mapping: dict[str, Any] | None) -> dict[int, str]:
    out: dict[int, str] = {}
    for key, value in (mapping or {}).items():
        parsed = _as_int(value)
        if parsed is not None:
            out[parsed] = str(key)
    return out


def _put_langs(bucket: dict[str, Any], langs: dict[str, str]) -> None:
    for code, text in langs.items():
        bucket[code] = text


def _translations_for(
    by_parent: dict[tuple[str, str, int], dict[str, str]],
    table: str,
    column: str,
    row_id: int | None,
) -> dict[str, str]:
    if row_id is None:
        return {}
    return dict(by_parent.get((table, column, row_id)) or {})


def extract_language_table(
    index: Any,
    explicit: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, int]]:
    """Build spec languageTable + ids.explicit.languageTables from transfer rows."""
    by_parent: dict[tuple[str, str, int], dict[str, str]] = {}
    lt_ids: dict[tuple[str, str, int, str], int] = {}
    for row in index.rows.get("LanguageTable") or []:
        if not _boolish(row.get("IsActive", 1)):
            continue
        table = str(row.get("TableName") or "")
        column = str(row.get("ColumnName") or "")
        row_id = _as_int(row.get("RowID"))
        lang = str(row.get("UserLanguageCode") or "")
        text = str(row.get("LanguageTableData") or "").strip()
        lt_id = _as_int(row.get("LanguageTableID"))
        if not table or not column or row_id is None or not lang or not text:
            continue
        by_parent.setdefault((table, column, row_id), {})[lang] = text
        if lt_id is not None:
            lt_ids[(table, column, row_id, lang)] = lt_id

    language_table: dict[str, Any] = {}
    explicit_lt: dict[str, int] = {}

    def record(table: str, column: str, entity_key: str, row_id: int, langs: dict[str, str]) -> None:
        if not langs:
            return
        for lang in langs:
            lt_id = lt_ids.get((table, column, row_id, lang))
            if lt_id is not None:
                explicit_lt[language_table_id_key(table, column, entity_key, lang)] = lt_id

    object_id = _as_int(explicit.get("objectId"))
    langs = _translations_for(by_parent, "Object", "ObjectName", object_id)
    if langs and object_id is not None:
        language_table["object"] = dict(langs)
        record("Object", "ObjectName", "object", object_id, langs)

    company_id = _as_int(explicit.get("companyId"))
    langs = _translations_for(by_parent, "Company", "CompanyName", company_id)
    if langs and company_id is not None:
        language_table["company"] = dict(langs)
        record("Company", "CompanyName", "company", company_id, langs)

    ot_id = _as_int(explicit.get("objectTypeId"))
    langs = _translations_for(by_parent, "ObjectType", "ObjectTypeName", ot_id)
    if langs and ot_id is not None:
        language_table["objectType"] = dict(langs)
        record("ObjectType", "ObjectTypeName", "objectType", ot_id, langs)

    wf_id = _as_int(explicit.get("workflowId"))
    langs = _translations_for(by_parent, "Workflow", "WorkflowName", wf_id)
    if langs and wf_id is not None:
        language_table["workflow"] = dict(langs)
        record("Workflow", "WorkflowName", "workflow", wf_id, langs)

    for kind, (table, column, category) in CATEGORY_TARGETS.items():
        bucket: dict[str, Any] = {}
        for row_id, key in _rev(explicit.get(category)).items():
            langs = _translations_for(by_parent, table, column, row_id)
            if not langs:
                continue
            bucket[key] = dict(langs)
            record(table, column, key, row_id, langs)
        if kind == "templates" and not bucket:
            default_id = _as_int(explicit.get("objectDefaultId"))
            langs = _translations_for(by_parent, table, column, default_id)
            if langs and default_id is not None:
                bucket["default"] = dict(langs)
                record(table, column, "default", default_id, langs)
        if bucket:
            language_table[kind] = bucket

    lines_bucket: dict[str, Any] = {}
    for row_id, code in _rev(explicit.get("fields")).items():
        name_langs = _translations_for(by_parent, "ObjectLine", "ObjectLineName", row_id)
        grid_langs = _translations_for(by_parent, "ObjectLine", "ObjectLineOnGridName", row_id)
        if not name_langs and not grid_langs:
            continue
        entry: dict[str, Any] = {}
        if name_langs:
            _put_langs(entry, name_langs)
            record("ObjectLine", "ObjectLineName", code, row_id, name_langs)
        if grid_langs:
            entry["onGrid"] = dict(grid_langs)
            record("ObjectLine", "ObjectLineOnGridName", code, row_id, grid_langs)
        lines_bucket[code] = entry
    if lines_bucket:
        language_table["lines"] = lines_bucket

    step_rev = _rev(explicit.get("workflowStepActions"))
    step_name_by_id = {
        int(row["WorkflowStepID"]): str(row.get("WorkflowStepName") or f"Step_{row['WorkflowStepID']}")
        for row in index.rows.get("WorkflowStep") or []
        if row.get("WorkflowStepID") is not None
    }
    step_actions: dict[str, Any] = {}
    for row_id, action_name in step_rev.items():
        langs = _translations_for(by_parent, "WorkflowStepAction", "WorkflowStepActionName", row_id)
        if not langs:
            continue
        wsa = index.row_by_id("WorkflowStepAction", row_id)
        step_name = action_name
        if wsa and wsa.get("WorkflowStepID") is not None:
            step_name = step_name_by_id.get(int(wsa["WorkflowStepID"]), action_name)
            action_label = str(wsa.get("WorkflowStepActionName") or action_name)
            entity_key = f"{step_name}/{action_label}"
        else:
            entity_key = str(action_name)
        step_actions[entity_key] = dict(langs)
        record("WorkflowStepAction", "WorkflowStepActionName", entity_key, row_id, langs)
    if step_actions:
        language_table["stepActions"] = step_actions

    return language_table, explicit_lt
