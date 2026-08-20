"""Shared helpers for ObjectAction spec extract/generate."""

from __future__ import annotations

from typing import Any

from ot_builder.ids import IdRegistry
from ot_builder.update_actions import condition_slug, condition_type_id, slugify

OBJECT_LINE_ID_PARAM_SUFFIX = "ObjectLineID"
ROLE_ID_PARAM_CODES = {"RoleID1"}
STATUS_ID_PARAM_CODES = {"RequestStatusID1"}


def param_registry_key(action_key: str, param_code: str) -> str:
    return f"{action_key}/{param_code}"


def condition_registry_key(action_key: str, field_code: str, type_slug: str) -> str:
    return f"{action_key}/{field_code}/{type_slug}"


def step_link_registry_key(action_key: str, step_name: str) -> str:
    return f"{action_key}/{step_name}"


def iter_params(action: dict[str, Any]) -> list[tuple[str, Any]]:
    params = action.get("params")
    if not params:
        return []
    if isinstance(params, dict):
        return list(params.items())
    items: list[tuple[str, Any]] = []
    for entry in params:
        items.append((str(entry["code"]), entry.get("value")))
    return items


def resolve_param_value(
    value: Any,
    *,
    param_code: str,
    registry: IdRegistry,
) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        if value.get("field"):
            return str(registry.require("fields", str(value["field"])))
        if value.get("role"):
            return str(registry.require("roles", str(value["role"])))
        if value.get("status"):
            return str(registry.require("statuses", str(value["status"])))
    if param_code.endswith(OBJECT_LINE_ID_PARAM_SUFFIX) and isinstance(value, str) and not value.isdigit():
        return str(registry.require("fields", value))
    return str(value)


def param_spec_value(
    param_code: str,
    raw_value: Any,
    field_id_to_code: dict[int, str],
    *,
    role_id_to_key: dict[int, str] | None = None,
    status_id_to_key: dict[int, str] | None = None,
) -> Any:
    if raw_value is None:
        return None
    text = str(raw_value)
    if param_code.endswith(OBJECT_LINE_ID_PARAM_SUFFIX) and text.isdigit():
        code = field_id_to_code.get(int(text))
        if code:
            return {"field": code}
    if text.isdigit():
        row_id = int(text)
        if param_code in ROLE_ID_PARAM_CODES:
            key = (role_id_to_key or {}).get(row_id)
            if key:
                return {"role": key}
        if param_code in STATUS_ID_PARAM_CODES:
            key = (status_id_to_key or {}).get(row_id)
            if key:
                return {"status": key}
    return raw_value if not isinstance(raw_value, str) else text
