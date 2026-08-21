"""Parse Xeelo DB transfer JSON (table name → row arrays)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ot_builder.parse import TransferIndex


def parse_db_transfer_json(data: bytes | str) -> dict[str, Any]:
    """Parse GraphQL DB-transfer JSON into the shared transfer dict shape."""
    text = data.decode("utf-8-sig") if isinstance(data, (bytes, bytearray)) else data
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid DB transfer JSON: {exc}") from exc
    if not isinstance(obj, dict) or isinstance(obj, list):
        raise ValueError("DB transfer JSON must be an object keyed by table name")

    rows: dict[str, list[dict]] = {}
    for table, table_rows in obj.items():
        if not isinstance(table, str) or not table:
            raise ValueError(f"Invalid table name in DB transfer JSON: {table!r}")
        if not isinstance(table_rows, list):
            raise ValueError(
                f"DB transfer table {table!r} must be an array of rows, "
                f"got {type(table_rows).__name__}"
            )
        parsed_rows: list[dict] = []
        for i, row in enumerate(table_rows):
            if not isinstance(row, dict) or isinstance(row, list):
                raise ValueError(
                    f"DB transfer {table}[{i}] must be an object, got {type(row).__name__}"
                )
            parsed_rows.append(row)
        rows[table] = parsed_rows

    return {
        "edges": [],
        "objectMap": [],
        "transferInfo": {},
        "rows": rows,
    }


def load_db_transfer(path: Path) -> dict[str, Any]:
    """Load a DB transfer JSON file (no XML/ZIP)."""
    path = Path(path)
    if path.suffix.lower() != ".json":
        raise ValueError(
            f"DB transfer must be a .json file, got {path}. "
            "Use extract-object-transfer-to-spec.py for Object Transfer XML."
        )
    return parse_db_transfer_json(path.read_bytes())


def db_index(path: Path) -> TransferIndex:
    return TransferIndex.from_parsed(load_db_transfer(path))


def collect_object_by_table(index: TransferIndex, object_id: int) -> dict[str, dict[str, int]]:
    """Collect ID inventory for an object using FK relationships (no ObjectSetup)."""
    by_table: dict[str, dict[str, int]] = {"Object": {str(object_id): object_id}}

    def add(table: str, row_id: Any) -> None:
        if row_id is None:
            return
        rid = int(row_id)
        by_table.setdefault(table, {})[str(rid)] = rid

    line_ids: set[int] = set()
    section_ids: set[int] = set()
    tab_ids: set[int] = set()
    default_ids: set[int] = set()
    workflow_ids: set[int] = set()
    sub_ids: set[int] = set()

    for row in index.rows_for("ObjectLine", "ObjectID", object_id):
        lid = int(row["ObjectLineID"])
        line_ids.add(lid)
        add("ObjectLine", lid)
        if row.get("ObjectLineSectionID") is not None:
            section_ids.add(int(row["ObjectLineSectionID"]))
        if row.get("ObjectSubID") is not None:
            sub_ids.add(int(row["ObjectSubID"]))
        if row.get("ObjectLineSourceID") is not None:
            add("ObjectLineSource", row["ObjectLineSourceID"])

    for sid in section_ids:
        sec = index.row_by_id("ObjectLineSection", sid)
        if not sec:
            continue
        add("ObjectLineSection", sid)
        if sec.get("ObjectLineTabID") is not None:
            tab_ids.add(int(sec["ObjectLineTabID"]))

    for tid in tab_ids:
        add("ObjectLineTab", tid)

    for row in index.rows_for("ObjectDefault", "ObjectID", object_id):
        did = int(row["ObjectDefaultID"])
        default_ids.add(did)
        add("ObjectDefault", did)
        if row.get("WorkflowID") is not None:
            workflow_ids.add(int(row["WorkflowID"]))
            add("Workflow", row["WorkflowID"])

    for row in index.rows_for_any("ObjectDefaultAccess", "ObjectDefaultID", default_ids):
        add("ObjectDefaultAccess", row.get("ObjectDefaultAccessID"))
        if row.get("ObjectLineID") is not None:
            add("ObjectLine", row["ObjectLineID"])

    for row in index.rows_for_any("ObjectDefaultLine", "ObjectDefaultID", default_ids):
        add("ObjectDefaultLine", row["ObjectDefaultLineID"])
        if row.get("ObjectDefaultLineLookupID") is not None:
            add("ObjectLineLookup", row["ObjectDefaultLineLookupID"])

    seen_ongrid: set[int] = set()
    for row in index.rows_for("ObjectLineOnGrid", "ObjectID", object_id):
        og_id = row.get("ObjectLineOnGridID")
        if og_id is not None:
            seen_ongrid.add(int(og_id))
        add("ObjectLineOnGrid", og_id)
    for lid in line_ids:
        for row in index.rows_for("ObjectLineOnGrid", "ObjectLineID", lid):
            og_id = row.get("ObjectLineOnGridID")
            if og_id is None or int(og_id) in seen_ongrid:
                continue
            seen_ongrid.add(int(og_id))
            add("ObjectLineOnGrid", og_id)

    for wf_id in workflow_ids:
        step_ids: set[int] = set()
        for row in index.rows_for("WorkflowStep", "WorkflowID", wf_id):
            sid = int(row["WorkflowStepID"])
            step_ids.add(sid)
            add("WorkflowStep", sid)
        for row in index.rows_for_any("WorkflowStepAction", "WorkflowStepID", step_ids):
            add("WorkflowStepAction", row.get("WorkflowStepActionID"))
        for row in index.rows_for_any("WorkflowStepAccess", "WorkflowStepID", step_ids):
            add("WorkflowStepAccess", row.get("WorkflowStepAccessID"))

    for sub_id in sub_ids:
        add("ObjectSub", sub_id)
        for row in index.rows_for("ObjectSubLine", "ObjectSubID", sub_id):
            add("ObjectSubLine", row.get("ObjectSubLineID"))
        for row in index.rows_for("ObjectSubDefault", "ObjectSubID", sub_id):
            add("ObjectSubDefault", row.get("ObjectSubDefaultID"))
        sub_section_ids = {
            int(r["ObjectSubLineSectionID"])
            for r in index.rows_for("ObjectSubLine", "ObjectSubID", sub_id)
            if r.get("ObjectSubLineSectionID") is not None
        }
        sub_tab_ids: set[int] = set()
        for ssid in sub_section_ids:
            sec = index.row_by_id("ObjectSubLineSection", ssid)
            if sec:
                add("ObjectSubLineSection", ssid)
                if sec.get("ObjectSubLineTabID") is not None:
                    sub_tab_ids.add(int(sec["ObjectSubLineTabID"]))
        for stid in sub_tab_ids:
            add("ObjectSubLineTab", stid)

    update_action_ids: set[int] = set()
    for row in index.rows_for("ObjectUpdateAction", "ObjectID", object_id):
        ua_id = int(row["ObjectUpdateActionID"])
        update_action_ids.add(ua_id)
        add("ObjectUpdateAction", ua_id)
        if row.get("WorkflowID") is not None:
            add("Workflow", row["WorkflowID"])
        if row.get("ObjectDefaultID") is not None:
            add("ObjectDefault", row["ObjectDefaultID"])

    for row in index.rows_for_any("ObjectUpdateAccess", "ObjectUpdateActionID", update_action_ids):
        add("ObjectUpdateAccess", row.get("ObjectUpdateAccessID"))
        if row.get("ObjectLineID") is not None:
            add("ObjectLine", row["ObjectLineID"])

    for row in index.rows_for_any(
        "ObjectUpdateActionCondition", "ObjectUpdateActionID", update_action_ids
    ):
        add("ObjectUpdateActionCondition", row.get("ObjectUpdateActionConditionID"))

    for row in index.rows_for_any("ObjectUpdateMessage", "ObjectUpdateActionID", update_action_ids):
        add("ObjectUpdateMessage", row.get("ObjectUpdateMessageID"))
        if row.get("ObjectMessageID") is not None:
            add("ObjectMessage", row["ObjectMessageID"])

    message_ids: set[int] = set()
    for row in index.rows_for("ObjectMessage", "ObjectID", object_id):
        om_id = int(row["ObjectMessageID"])
        message_ids.add(om_id)
        add("ObjectMessage", om_id)
    for row in index.rows_for_any("ObjectMessageCondition", "ObjectMessageID", message_ids):
        add("ObjectMessageCondition", row.get("ObjectMessageConditionID"))

    action_ids: set[int] = set()
    for row in index.rows_for("ObjectAction", "ObjectID", object_id):
        action_id = int(row["ObjectActionID"])
        action_ids.add(action_id)
        add("ObjectAction", action_id)

    for row in index.rows_for_any("ObjectActionParam", "ObjectActionID", action_ids):
        add("ObjectActionParam", row.get("ObjectActionParamID"))

    for row in index.rows_for_any("ObjectActionCondition", "ObjectActionID", action_ids):
        add("ObjectActionCondition", row.get("ObjectActionConditionID"))

    for row in index.rows_for_any("WorkflowStepObjectAction", "ObjectActionID", action_ids):
        add("WorkflowStepObjectAction", row.get("WorkflowStepObjectActionID"))
        if row.get("WorkflowStepID") is not None:
            add("WorkflowStep", row["WorkflowStepID"])

    obj = index.row_by_id("Object", object_id)
    if obj:
        add("ObjectType", obj.get("ObjectTypeID"))
        add("Company", obj.get("CompanyID"))

    owned = {
        table: {int(row_id) for row_id in ids.values()}
        for table, ids in by_table.items()
    }
    lt_by_parent = index.group_by("LanguageTable", "TableName", "RowID")
    for parent_table, ids in owned.items():
        for rid in ids:
            for row in lt_by_parent.get((parent_table, rid), []):
                if row.get("LanguageTableID") is not None:
                    add("LanguageTable", row["LanguageTableID"])

    return by_table


# re-export for callers
__all__ = [
    "parse_db_transfer_json",
    "load_db_transfer",
    "db_index",
    "collect_object_by_table",
    "TransferIndex",
]
