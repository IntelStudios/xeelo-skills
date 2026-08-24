"""Emit and extract TableComments rows from spec comments maps."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ot_builder.ids import IdRegistry
from ot_builder.language_table import (
    CATEGORY_TARGETS,
    SCALAR_TARGETS,
    REUSED_WORKFLOW_SKIP_KINDS,
    _as_int,
    _rev,
    _workflow_reused,
)

DEFAULT_USER_NAME = "xeelo-skills"

KNOWN_TYPES = frozenset(
    {
        *SCALAR_TARGETS,
        *CATEGORY_TARGETS,
        "lines",
        "stepActions",
        "templateHints",
        "objectMessages",
    }
)


def table_comment_id_key(table: str, entity_key: str, index: int) -> str:
    return f"{table}:{entity_key}:{index}"


def _comment_date(value: Any, *, fallback: str) -> str:
    if value is None:
        return fallback
    if isinstance(value, datetime):
        return value.replace(microsecond=0).isoformat()
    text = str(value).strip()
    return text or fallback


def _now_stamp() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def _comment_items(body: Any, *, kind: str) -> list[dict[str, Any]]:
    if body is None:
        return []
    if not isinstance(body, list):
        raise ValueError(f"comments.{kind} must be a list of comment objects")
    items: list[dict[str, Any]] = []
    for i, raw in enumerate(body):
        if isinstance(raw, str):
            html = raw.strip()
            if html:
                items.append({"html": html})
            continue
        if not isinstance(raw, dict):
            raise ValueError(f"comments.{kind}[{i}]: expected mapping or HTML string")
        html = str(raw.get("html") or "").strip()
        if not html:
            continue
        item: dict[str, Any] = {"html": html}
        user_name = raw.get("userName")
        if isinstance(user_name, str) and user_name.strip():
            item["userName"] = user_name.strip()
        date = raw.get("date")
        if date is not None and str(date).strip():
            item["date"] = _comment_date(date, fallback="")
        items.append(item)
    return items


def _require_parent(registry: IdRegistry, category: str, key: str, *, kind: str) -> int:
    parent_id = registry.get(category, key)
    if parent_id is None:
        raise ValueError(f"comments.{kind}: unknown key {key!r}")
    return parent_id


def _require_scalar(registry: IdRegistry, scalar: str, *, kind: str) -> int:
    parent_id = registry.get_scalar(scalar)
    if parent_id is None:
        raise ValueError(f"comments.{kind}: parent {scalar} is not allocated")
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
    raise ValueError(f"comments.stepActions: unknown key {key!r}")


def _template_hint_parent_id(registry: IdRegistry, template_key: str, field_code: str) -> int:
    composite = f"{template_key}/{field_code}"
    known = registry.get("objectDefaultLines", composite)
    if known is not None:
        return known
    known = registry.get("objectDefaultLines", str(field_code))
    if known is not None:
        return known
    raise ValueError(f"comments.templateHints: unknown template line {template_key}/{field_code}")


def _emit_items(
    result: Any,
    registry: IdRegistry,
    *,
    parent_table: str,
    parent_id: int,
    entity_key: str,
    items: list[dict[str, Any]],
    stamp: str,
) -> None:
    for index, item in enumerate(items):
        composite = table_comment_id_key(parent_table, entity_key, index)
        comment_id = registry.require("tableComments", composite)
        user_name = str(item.get("userName") or DEFAULT_USER_NAME)
        date = _comment_date(item.get("date"), fallback=stamp)
        result.rows.setdefault("TableComments", []).append(
            {
                "TableCommentID": comment_id,
                "TableName": parent_table,
                "TableRowID": parent_id,
                "UserID": 0,
                "UserName": user_name,
                "TableCommentData": item["html"],
                "TableCommentDate": date,
            }
        )
        result.edges.append(
            {
                "TableName": parent_table,
                "TableRowID": parent_id,
                "ChildTableName": "TableComments",
                "ChildTableRowID": comment_id,
            }
        )


def emit_comments(spec: dict, registry: IdRegistry, result: Any) -> None:
    payload = spec.get("comments") or {}
    if not payload:
        return
    if not isinstance(payload, dict):
        raise ValueError("comments must be a mapping")

    stamp = _now_stamp()
    skip_kinds = REUSED_WORKFLOW_SKIP_KINDS if _workflow_reused(spec) else frozenset()
    for kind, body in payload.items():
        if kind not in KNOWN_TYPES:
            raise ValueError(f"comments: unknown type {kind!r}")
        if kind in skip_kinds:
            continue
        if kind in SCALAR_TARGETS:
            table, _column, scalar = SCALAR_TARGETS[kind]
            items = _comment_items(body, kind=kind)
            if not items:
                continue
            parent_id = _require_scalar(registry, scalar, kind=kind)
            _emit_items(
                result,
                registry,
                parent_table=table,
                parent_id=parent_id,
                entity_key=kind,
                items=items,
                stamp=stamp,
            )
            continue
        if kind == "lines":
            if not isinstance(body, dict):
                raise ValueError("comments.lines must be a mapping")
            for code, entry in body.items():
                items = _comment_items(entry, kind=f"lines.{code}")
                if not items:
                    continue
                parent_id = _require_parent(registry, "fields", str(code), kind="lines")
                _emit_items(
                    result,
                    registry,
                    parent_table="ObjectLine",
                    parent_id=parent_id,
                    entity_key=str(code),
                    items=items,
                    stamp=stamp,
                )
            continue
        if kind == "templateHints":
            if not isinstance(body, dict):
                raise ValueError("comments.templateHints must be a mapping")
            for template_key, fields in body.items():
                if not isinstance(fields, dict):
                    raise ValueError(
                        f"comments.templateHints.{template_key}: expected mapping"
                    )
                for field_code, entry in fields.items():
                    items = _comment_items(
                        entry, kind=f"templateHints.{template_key}.{field_code}"
                    )
                    if not items:
                        continue
                    parent_id = _template_hint_parent_id(
                        registry, str(template_key), str(field_code)
                    )
                    _emit_items(
                        result,
                        registry,
                        parent_table="ObjectDefaultLine",
                        parent_id=parent_id,
                        entity_key=f"{template_key}/{field_code}",
                        items=items,
                        stamp=stamp,
                    )
            continue
        if kind == "objectMessages":
            if not isinstance(body, dict):
                raise ValueError("comments.objectMessages must be a mapping")
            for key, entry in body.items():
                items = _comment_items(entry, kind=f"objectMessages.{key}")
                if not items:
                    continue
                parent_id = _require_parent(
                    registry, "objectMessages", str(key), kind="objectMessages"
                )
                _emit_items(
                    result,
                    registry,
                    parent_table="ObjectMessage",
                    parent_id=parent_id,
                    entity_key=str(key),
                    items=items,
                    stamp=stamp,
                )
            continue
        if kind == "stepActions":
            if not isinstance(body, dict):
                raise ValueError("comments.stepActions must be a mapping")
            for key, entry in body.items():
                items = _comment_items(entry, kind=f"stepActions.{key}")
                if not items:
                    continue
                parent_id = _step_action_id(registry, str(key))
                _emit_items(
                    result,
                    registry,
                    parent_table="WorkflowStepAction",
                    parent_id=parent_id,
                    entity_key=str(key),
                    items=items,
                    stamp=stamp,
                )
            continue
        table, _column, category = CATEGORY_TARGETS[kind]
        if not isinstance(body, dict):
            raise ValueError(f"comments.{kind} must be a mapping")
        for key, entry in body.items():
            items = _comment_items(entry, kind=f"{kind}.{key}")
            if not items:
                continue
            parent_id = _require_parent(registry, category, str(key), kind=kind)
            _emit_items(
                result,
                registry,
                parent_table=table,
                parent_id=parent_id,
                entity_key=str(key),
                items=items,
                stamp=stamp,
            )


def _sort_key(row: dict) -> tuple:
    date = str(row.get("TableCommentDate") or "")
    comment_id = _as_int(row.get("TableCommentID")) or 0
    return (date, comment_id)


def _comments_for(
    by_parent: dict[tuple[Any, Any], list[dict]],
    table: str,
    row_id: int | None,
) -> list[dict]:
    if row_id is None:
        return []
    rows = list(by_parent.get((table, row_id), []))
    rows.sort(key=_sort_key)
    return rows


def _item_from_row(row: dict) -> dict[str, Any] | None:
    html = str(row.get("TableCommentData") or "").strip()
    if not html:
        return None
    item: dict[str, Any] = {"html": html}
    user_name = str(row.get("UserName") or "").strip()
    if user_name:
        item["userName"] = user_name
    date = row.get("TableCommentDate")
    if date is not None and str(date).strip():
        item["date"] = _comment_date(date, fallback="")
        if not item["date"]:
            item.pop("date", None)
    return item


def _comment_row_map(index: Any) -> dict[tuple[Any, Any], list[dict]]:
    cached = getattr(index, "_xeelo_tc_map", None)
    if cached is not None:
        return cached
    grouped = index.group_by("TableComments", "TableName", "TableRowID")
    try:
        index._xeelo_tc_map = grouped
    except Exception:
        pass
    return grouped


def extract_comments(
    index: Any,
    explicit: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, int]]:
    """Build spec comments + ids.explicit.tableComments from transfer rows."""
    by_parent = _comment_row_map(index)
    comments: dict[str, Any] = {}
    explicit_tc: dict[str, int] = {}

    def record(table: str, entity_key: str, row_id: int, rows: list[dict]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for index_pos, row in enumerate(rows):
            item = _item_from_row(row)
            if item is None:
                continue
            items.append(item)
            comment_id = _as_int(row.get("TableCommentID"))
            if comment_id is not None:
                explicit_tc[table_comment_id_key(table, entity_key, index_pos)] = comment_id
        return items

    object_id = _as_int(explicit.get("objectId"))
    rows = _comments_for(by_parent, "Object", object_id)
    if rows and object_id is not None:
        items = record("Object", "object", object_id, rows)
        if items:
            comments["object"] = items

    company_id = _as_int(explicit.get("companyId"))
    rows = _comments_for(by_parent, "Company", company_id)
    if rows and company_id is not None:
        items = record("Company", "company", company_id, rows)
        if items:
            comments["company"] = items

    ot_id = _as_int(explicit.get("objectTypeId"))
    rows = _comments_for(by_parent, "ObjectType", ot_id)
    if rows and ot_id is not None:
        items = record("ObjectType", "objectType", ot_id, rows)
        if items:
            comments["objectType"] = items

    wf_id = _as_int(explicit.get("workflowId"))
    rows = _comments_for(by_parent, "Workflow", wf_id)
    if rows and wf_id is not None:
        items = record("Workflow", "workflow", wf_id, rows)
        if items:
            comments["workflow"] = items

    for kind, (table, _column, category) in CATEGORY_TARGETS.items():
        bucket: dict[str, Any] = {}
        for row_id, key in _rev(explicit.get(category)).items():
            found = _comments_for(by_parent, table, row_id)
            if not found:
                continue
            items = record(table, key, row_id, found)
            if items:
                bucket[key] = items
        if kind == "templates" and not bucket:
            default_id = _as_int(explicit.get("objectDefaultId"))
            found = _comments_for(by_parent, table, default_id)
            if found and default_id is not None:
                items = record(table, "default", default_id, found)
                if items:
                    bucket["default"] = items
        if bucket:
            comments[kind] = bucket

    lines_bucket: dict[str, Any] = {}
    for row_id, code in _rev(explicit.get("fields")).items():
        found = _comments_for(by_parent, "ObjectLine", row_id)
        if not found:
            continue
        items = record("ObjectLine", code, row_id, found)
        if items:
            lines_bucket[code] = items
    if lines_bucket:
        comments["lines"] = lines_bucket

    step_rev = _rev(explicit.get("workflowStepActions"))
    step_key_by_id = _rev(explicit.get("workflowSteps"))
    step_name_by_id = {
        int(row["WorkflowStepID"]): str(row.get("WorkflowStepName") or f"Step_{row['WorkflowStepID']}")
        for row in index.rows.get("WorkflowStep") or []
        if row.get("WorkflowStepID") is not None
    }
    step_actions: dict[str, Any] = {}
    for row_id, action_key in step_rev.items():
        found = _comments_for(by_parent, "WorkflowStepAction", row_id)
        if not found:
            continue
        wsa = index.row_by_id("WorkflowStepAction", row_id)
        entity_key = str(action_key)
        if wsa and wsa.get("WorkflowStepID") is not None:
            sid = int(wsa["WorkflowStepID"])
            step_key = step_key_by_id.get(sid) or step_name_by_id.get(sid) or str(action_key)
            entity_key = f"{step_key}/{action_key}"
        items = record("WorkflowStepAction", entity_key, row_id, found)
        if items:
            step_actions[entity_key] = items
    if step_actions:
        comments["stepActions"] = step_actions

    om_bucket: dict[str, Any] = {}
    for row_id, key in _rev(explicit.get("objectMessages")).items():
        found = _comments_for(by_parent, "ObjectMessage", row_id)
        if not found:
            continue
        items = record("ObjectMessage", key, row_id, found)
        if items:
            om_bucket[key] = items
    if om_bucket:
        comments["objectMessages"] = om_bucket

    templates_map = explicit.get("templates") or {}
    single_template_key = next(iter(templates_map), "default") if len(templates_map) <= 1 else None
    hint_bucket: dict[str, Any] = {}
    for row_id, key in _rev(explicit.get("objectDefaultLines")).items():
        found = _comments_for(by_parent, "ObjectDefaultLine", row_id)
        if not found:
            continue
        if "/" in str(key):
            template_key, field_code = str(key).split("/", 1)
        elif single_template_key is not None:
            template_key, field_code = str(single_template_key), str(key)
        else:
            continue
        items = record(
            "ObjectDefaultLine",
            f"{template_key}/{field_code}",
            row_id,
            found,
        )
        if items:
            hint_bucket.setdefault(template_key, {})[field_code] = items
    if hint_bucket:
        comments["templateHints"] = hint_bucket

    return comments, explicit_tc
