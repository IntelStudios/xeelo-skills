"""Parse Xeelo DB transfer (UTF-16 multi-block ZIP/XML, TransferType=DB)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ot_builder.parse import TransferIndex, load_transfer, parse_transfer_bytes


def load_db_transfer(path: Path) -> dict[str, Any]:
    """Load DB transfer ZIP/XML and validate TransferType=DB."""
    parsed = load_transfer(path)
    info = parsed.get("transferInfo") or {}
    transfer_type = str(info.get("TransferType") or info.get("transferType") or "")
    if transfer_type and transfer_type.upper() != "DB":
        raise ValueError(
            f"Expected TransferType=DB, got {transfer_type!r} in {path}. "
            "Use extract-object-transfer-to-spec.py for Object transfers."
        )
    if not transfer_type:
        # Still accept packages that look like DB (no ObjectSetup edges, has table blocks).
        if parsed.get("edges"):
            raise ValueError(
                f"Transfer has ObjectSetup edges but no TransferType=DB in {path}"
            )
    return parsed


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

    for row in index.rows.get("ObjectLine", []):
        if int(row.get("ObjectID", 0)) != object_id:
            continue
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

    for row in index.rows.get("ObjectDefault", []):
        if int(row.get("ObjectID", 0)) != object_id:
            continue
        did = int(row["ObjectDefaultID"])
        default_ids.add(did)
        add("ObjectDefault", did)
        if row.get("WorkflowID") is not None:
            workflow_ids.add(int(row["WorkflowID"]))
            add("Workflow", row["WorkflowID"])

    for row in index.rows.get("ObjectDefaultAccess", []):
        if int(row.get("ObjectDefaultID", 0)) not in default_ids:
            continue
        add("ObjectDefaultAccess", row.get("ObjectDefaultAccessID"))
        if row.get("ObjectLineID") is not None:
            add("ObjectLine", row["ObjectLineID"])

    default_line_ids: set[int] = set()
    for row in index.rows.get("ObjectDefaultLine", []):
        if int(row.get("ObjectDefaultID", 0)) not in default_ids:
            continue
        dlid = int(row["ObjectDefaultLineID"])
        default_line_ids.add(dlid)
        add("ObjectDefaultLine", dlid)
        if row.get("ObjectDefaultLineLookupID") is not None:
            add("ObjectLineLookup", row["ObjectDefaultLineLookupID"])

    for row in index.rows.get("ObjectLineOnGrid", []):
        if int(row.get("ObjectID", 0)) == object_id or int(row.get("ObjectLineID", 0)) in line_ids:
            add("ObjectLineOnGrid", row.get("ObjectLineOnGridID"))

    for wf_id in workflow_ids:
        step_ids: set[int] = set()
        for row in index.rows.get("WorkflowStep", []):
            if int(row.get("WorkflowID", 0)) != wf_id:
                continue
            sid = int(row["WorkflowStepID"])
            step_ids.add(sid)
            add("WorkflowStep", sid)
        for row in index.rows.get("WorkflowStepAction", []):
            if int(row.get("WorkflowStepID", 0)) in step_ids:
                add("WorkflowStepAction", row.get("WorkflowStepActionID"))
        for row in index.rows.get("WorkflowStepAccess", []):
            if int(row.get("WorkflowStepID", 0)) in step_ids:
                add("WorkflowStepAccess", row.get("WorkflowStepAccessID"))

    for sub_id in sub_ids:
        add("ObjectSub", sub_id)
        for row in index.rows.get("ObjectSubLine", []):
            if int(row.get("ObjectSubID", 0)) == sub_id:
                add("ObjectSubLine", row.get("ObjectSubLineID"))
        for row in index.rows.get("ObjectSubDefault", []):
            if int(row.get("ObjectSubID", 0)) == sub_id:
                add("ObjectSubDefault", row.get("ObjectSubDefaultID"))
        for row in index.rows.get("ObjectSubLineTab", []):
            # Tabs for subs are linked via sections on sub lines
            pass
        sub_section_ids = {
            int(r["ObjectSubLineSectionID"])
            for r in index.rows.get("ObjectSubLine", [])
            if int(r.get("ObjectSubID", 0)) == sub_id and r.get("ObjectSubLineSectionID") is not None
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
    for row in index.rows.get("ObjectUpdateAction", []):
        if int(row.get("ObjectID", 0)) != object_id:
            continue
        ua_id = int(row["ObjectUpdateActionID"])
        update_action_ids.add(ua_id)
        add("ObjectUpdateAction", ua_id)
        if row.get("WorkflowID") is not None:
            add("Workflow", row["WorkflowID"])
        if row.get("ObjectDefaultID") is not None:
            add("ObjectDefault", row["ObjectDefaultID"])

    for row in index.rows.get("ObjectUpdateAccess", []):
        if int(row.get("ObjectUpdateActionID", 0)) in update_action_ids:
            add("ObjectUpdateAccess", row.get("ObjectUpdateAccessID"))
            if row.get("ObjectLineID") is not None:
                add("ObjectLine", row["ObjectLineID"])

    for row in index.rows.get("ObjectUpdateActionCondition", []):
        if int(row.get("ObjectUpdateActionID", 0)) in update_action_ids:
            add("ObjectUpdateActionCondition", row.get("ObjectUpdateActionConditionID"))

    for row in index.rows.get("ObjectUpdateMessage", []):
        if int(row.get("ObjectUpdateActionID", 0)) in update_action_ids:
            add("ObjectUpdateMessage", row.get("ObjectUpdateMessageID"))
            if row.get("ObjectMessageID") is not None:
                add("ObjectMessage", row["ObjectMessageID"])

    action_ids: set[int] = set()
    for row in index.rows.get("ObjectAction", []):
        if int(row.get("ObjectID", 0)) != object_id:
            continue
        action_id = int(row["ObjectActionID"])
        action_ids.add(action_id)
        add("ObjectAction", action_id)

    for row in index.rows.get("ObjectActionParam", []):
        if int(row.get("ObjectActionID", 0)) in action_ids:
            add("ObjectActionParam", row.get("ObjectActionParamID"))

    for row in index.rows.get("ObjectActionCondition", []):
        if int(row.get("ObjectActionID", 0)) in action_ids:
            add("ObjectActionCondition", row.get("ObjectActionConditionID"))

    for row in index.rows.get("WorkflowStepObjectAction", []):
        if int(row.get("ObjectActionID", 0)) in action_ids:
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
    for row in index.rows.get("LanguageTable", []):
        parent_table = str(row.get("TableName") or "")
        parent_id = row.get("RowID")
        try:
            rid = int(parent_id)
        except (TypeError, ValueError):
            continue
        if rid in owned.get(parent_table, set()) and row.get("LanguageTableID") is not None:
            add("LanguageTable", row["LanguageTableID"])

    return by_table


# re-export for callers
__all__ = [
    "load_db_transfer",
    "db_index",
    "collect_object_by_table",
    "parse_transfer_bytes",
    "load_transfer",
    "TransferIndex",
]
