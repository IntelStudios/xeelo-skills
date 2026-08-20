"""Shared helpers for ObjectUpdateAction spec extract/generate."""

from __future__ import annotations

import re
from typing import Any

# SmarterMDM seed ObjectUpdateActionConditionType (070_SyncTables_Object.sql)
CONDITION_ID_TO_SLUG: dict[int, str] = {
    0: "none",
    1: "contains",
    2: "does_not_contain",
    3: "begins_with",
    4: "does_not_begin_with",
    5: "ends_with",
    6: "does_not_end_with",
    7: "greater_than",
    8: "greater_than_or_equal",
    9: "less_than",
    10: "less_than_or_equal",
    11: "between",
    12: "not_between",
    13: "equals_text",
    14: "does_not_equal_text",
    15: "equals_number",
    16: "does_not_equal_number",
    17: "is_empty",
    18: "is_not_empty",
}

CONDITION_SLUG_TO_ID: dict[str, int] = {v: k for k, v in CONDITION_ID_TO_SLUG.items() if k != 0}


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", name.strip().lower()).strip("_")
    return slug or "update_action"


def condition_slug(type_id: int) -> str | None:
    slug = CONDITION_ID_TO_SLUG.get(int(type_id))
    if slug in (None, "none"):
        return None
    return slug


def condition_type_id(slug: str) -> int:
    if slug not in CONDITION_SLUG_TO_ID:
        raise ValueError(f"Unknown update condition type: {slug!r}")
    return CONDITION_SLUG_TO_ID[slug]


def access_registry_key(action_key: str, field_code: str, subline_id: int | None = None) -> str:
    if subline_id is not None:
        return f"{action_key}/{field_code}/sub{subline_id}"
    return f"{action_key}/{field_code}"


def access_differs_from_default(row: dict[str, Any]) -> bool:
    editable = bool(row.get("ObjectLineIsEditableUpdate", 0))
    visible = bool(row.get("ObjectLineIsVisibleUpdate", 1))
    subline = row.get("ObjectSubLineID")
    return editable or not visible or subline is not None


def template_access_differs_from_default(row: dict[str, Any]) -> bool:
    """Refresh seeds ObjectDefaultAccess as visible+editable (both 1)."""
    editable = bool(row.get("ObjectLineIsEditableCreate", 1))
    visible = bool(row.get("ObjectLineIsVisibleCreate", 1))
    subline = row.get("ObjectSubLineID")
    return (not editable) or (not visible) or subline is not None


def resolve_access_flags(access: dict[str, Any]) -> tuple[int, int]:
    """Return (editable, visible) bits. Editable implies visible (platform trigger)."""
    editable_bit = 1 if access.get("editable") else 0
    if editable_bit:
        return 1, 1
    if access.get("visible") is False:
        return 0, 0
    return 0, 1


def step_access_registry_key(step_name: str, field_code: str, subline_id: int | None = None) -> str:
    if subline_id is not None:
        return f"{step_name}/{field_code}/sub{subline_id}"
    return f"{step_name}/{field_code}"


def workflow_step_key(step: dict) -> str:
    return str(step.get("key") or step["name"])


def workflow_step_action_key(action: dict) -> str:
    return str(action.get("key") or action["name"])


def require_workflow_step_action_id(registry: Any, action: dict) -> int:
    """Reuse WorkflowStepAction IDs from extract (unique name or ``{slug}_{id}``)."""
    preferred = workflow_step_action_key(action)
    known = registry.get("workflowStepActions", preferred)
    if known is not None:
        return known
    name = str(action.get("name") or "")
    if name and name != preferred:
        known = registry.get("workflowStepActions", name)
        if known is not None:
            return known
    return registry.require("workflowStepActions", preferred)


def step_access_differs_from_default(row: dict[str, Any]) -> bool:
    editable = bool(row.get("WorkflowStepAccessIsEditable", 0))
    visible = bool(row.get("WorkflowStepAccessIsVisible", 1))
    subline = row.get("ObjectSubLineID")
    return editable or not visible or subline is not None
