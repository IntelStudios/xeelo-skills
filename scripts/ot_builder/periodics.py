"""Periodic + Scheduler spec extract/generate."""

from __future__ import annotations

from typing import Any

from ot_builder.ids import IdRegistry
from ot_builder.object_actions import (
    iter_params,
    param_spec_value,
    resolve_param_value,
)
from ot_builder.notifications import NOTIFICATION_ID_PARAM_CODES
from ot_builder.update_actions import condition_slug, condition_type_id, slugify

NODEJS_TYPE = "spEndPointRunNodeJSMain"
NODEJS_PARAM_DEFAULTS = {
    "EndPointRunESM": "1",
    "EndPointRunWait": "1",
    "EndPointRunTimeout": "60000",
}

SCHEDULER_LINE_TYPE = "spPeriodicExecute"
SCHEDULER_LINE_PARAM = "PeriodicID"
SCHEDULER_LINE_NAME = "Execute"

REQUEST_TYPE_SLUG_TO_ID = {
    "all": 0,
    "in_progress": 10,
    "completed": 20,
}
REQUEST_TYPE_ID_TO_SLUG = {v: k for k, v in REQUEST_TYPE_SLUG_TO_ID.items()}


def _boolish(val: Any) -> bool:
    return str(val) in ("1", "True", "true")


def action_registry_key(periodic_key: str, action_key: str) -> str:
    return f"{periodic_key}/{action_key}"


def condition_registry_key(periodic_key: str, field_code: str, type_slug: str) -> str:
    return f"{periodic_key}/{field_code}/{type_slug}"


def action_param_registry_key(periodic_key: str, action_key: str, param_code: str) -> str:
    return f"{periodic_key}/{action_key}/{param_code}"


def action_condition_registry_key(
    periodic_key: str, action_key: str, field_code: str, type_slug: str
) -> str:
    return f"{periodic_key}/{action_key}/{field_code}/{type_slug}"


def scheduler_line_registry_key(periodic_key: str) -> str:
    return f"{periodic_key}/execute"


def scheduler_line_param_registry_key(periodic_key: str) -> str:
    return f"{periodic_key}/execute/{SCHEDULER_LINE_PARAM}"


def request_type_id(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, bool):
        raise ValueError(f"Invalid periodic requestType: {value!r}")
    if isinstance(value, int):
        if value in REQUEST_TYPE_ID_TO_SLUG:
            return value
        raise ValueError(f"Unknown periodic requestType id: {value!r}")
    text = str(value).strip()
    if text.isdigit():
        return request_type_id(int(text))
    slug = text.lower().replace("-", "_").replace(" ", "_")
    if slug in REQUEST_TYPE_SLUG_TO_ID:
        return REQUEST_TYPE_SLUG_TO_ID[slug]
    raise ValueError(f"Unknown periodic requestType: {value!r}")


def request_type_slug(type_id: int) -> str:
    slug = REQUEST_TYPE_ID_TO_SLUG.get(int(type_id))
    if slug is None:
        raise ValueError(f"Unknown PeriodicRequestTypeID: {type_id!r}")
    return slug


def merge_nodejs_params(type_code: str, params: dict[str, Any]) -> dict[str, Any]:
    merged = dict(params)
    if type_code == NODEJS_TYPE:
        for key, default in NODEJS_PARAM_DEFAULTS.items():
            merged.setdefault(key, default)
    return merged


def _append_edge(
    result: Any, parent_table: str, parent_id: int, child_table: str, child_id: int
) -> None:
    result.edges.append(
        {
            "TableName": parent_table,
            "TableRowID": parent_id,
            "ChildTableName": child_table,
            "ChildTableRowID": child_id,
        }
    )


def _emit_conditions(
    *,
    conditions: list[dict[str, Any]],
    registry: IdRegistry,
    result: Any,
    parent_table: str,
    parent_id: int,
    parent_fk: str,
    condition_table: str,
    id_column: str,
    type_column: str,
    param1_column: str,
    param2_column: str,
    registry_category: str,
    registry_key_fn,
) -> list[dict]:
    rows: list[dict] = []
    for cond in conditions:
        field_code = str(cond["field"])
        type_slug = str(cond["type"])
        cond_id = registry.require(registry_category, registry_key_fn(field_code, type_slug))
        row = {
            parent_fk: parent_id,
            id_column: cond_id,
            "ObjectLineID": registry.require("fields", field_code),
            type_column: condition_type_id(type_slug),
            param1_column: cond.get("param1"),
            param2_column: cond.get("param2"),
            "IsActive": 1 if cond.get("isActive", True) else 0,
        }
        rows.append(row)
        _append_edge(result, parent_table, parent_id, condition_table, cond_id)
    return rows


def build_periodics(spec: dict, registry: IdRegistry, oid: int, result: Any) -> None:
    periodics = spec.get("periodics") or []
    if not periodics:
        return

    periodic_rows: list[dict] = []
    condition_rows: list[dict] = []
    action_rows: list[dict] = []
    param_rows: list[dict] = []
    action_condition_rows: list[dict] = []
    scheduler_rows: list[dict] = []
    scheduler_line_rows: list[dict] = []
    scheduler_param_rows: list[dict] = []

    for periodic in periodics:
        periodic_key = periodic.get("key") or slugify(str(periodic.get("name", "periodic")))
        periodic_id = registry.require("periodics", periodic_key)
        periodic_name = periodic.get("name", periodic_key)
        periodic_rows.append(
            {
                "PeriodicID": periodic_id,
                "PeriodicName": periodic_name,
                "ObjectID": oid,
                "PeriodicRequestTypeID": request_type_id(periodic.get("requestType")),
                "IsActive": 1 if periodic.get("isActive", True) else 0,
            }
        )
        _append_edge(result, "Object", oid, "Periodic", periodic_id)

        condition_rows.extend(
            _emit_conditions(
                conditions=periodic.get("conditions") or [],
                registry=registry,
                result=result,
                parent_table="Periodic",
                parent_id=periodic_id,
                parent_fk="PeriodicID",
                condition_table="PeriodicCondition",
                id_column="PeriodicConditionID",
                type_column="PeriodicConditionTypeID",
                param1_column="PeriodicConditionParam1",
                param2_column="PeriodicConditionParam2",
                registry_category="periodicConditions",
                registry_key_fn=lambda field, typ, key=periodic_key: condition_registry_key(
                    key, field, typ
                ),
            )
        )

        for action in periodic.get("actions") or []:
            action_key = action.get("key") or slugify(str(action.get("name", "periodic_action")))
            action_id = registry.require(
                "periodicActions", action_registry_key(periodic_key, action_key)
            )
            type_code = str(action["typeCode"])
            action_rows.append(
                {
                    "PeriodicID": periodic_id,
                    "PeriodicActionID": action_id,
                    "PeriodicActionName": action.get("name", action_key),
                    "PeriodicActionTypeCode": type_code,
                    "PeriodicActionOrder": action.get("order", 10),
                    "IsActive": 1 if action.get("isActive", True) else 0,
                }
            )
            _append_edge(result, "Periodic", periodic_id, "PeriodicAction", action_id)

            params = merge_nodejs_params(type_code, dict(iter_params(action)))
            for param_code, raw_value in params.items():
                param_id = registry.require(
                    "periodicActionParams",
                    action_param_registry_key(periodic_key, action_key, param_code),
                )
                resolved = resolve_param_value(
                    raw_value, param_code=param_code, registry=registry
                )
                param_rows.append(
                    {
                        "PeriodicActionID": action_id,
                        "PeriodicActionParamID": param_id,
                        "PeriodicActionTypeParamCode": param_code,
                        "PeriodicActionParamValue": resolved,
                        "IsActive": 1,
                    }
                )
                _append_edge(result, "PeriodicAction", action_id, "PeriodicActionParam", param_id)
                if (
                    param_code in NOTIFICATION_ID_PARAM_CODES
                    and resolved is not None
                    and str(resolved).isdigit()
                ):
                    _append_edge(result, "PeriodicAction", action_id, "Notification", int(resolved))

            action_condition_rows.extend(
                _emit_conditions(
                    conditions=action.get("conditions") or [],
                    registry=registry,
                    result=result,
                    parent_table="PeriodicAction",
                    parent_id=action_id,
                    parent_fk="PeriodicActionID",
                    condition_table="PeriodicActionCondition",
                    id_column="PeriodicActionConditionID",
                    type_column="PeriodicActionConditionTypeID",
                    param1_column="PeriodicActionConditionParam1",
                    param2_column="PeriodicActionConditionParam2",
                    registry_category="periodicActionConditions",
                    registry_key_fn=lambda field, typ, pkey=periodic_key, akey=action_key: (
                        action_condition_registry_key(pkey, akey, field, typ)
                    ),
                )
            )

        cron = periodic.get("cron")
        if cron:
            scheduler_id = registry.require("schedulers", periodic_key)
            scheduler_name = periodic.get("schedulerName") or periodic_name
            scheduler_rows.append(
                {
                    "SchedulerID": scheduler_id,
                    "SchedulerName": scheduler_name,
                    "SchedulerCRON": str(cron),
                    "IsActive": 1 if periodic.get("isActive", True) else 0,
                }
            )
            line_id = registry.require("schedulerLines", scheduler_line_registry_key(periodic_key))
            scheduler_line_rows.append(
                {
                    "SchedulerID": scheduler_id,
                    "SchedulerLineID": line_id,
                    "SchedulerLineName": SCHEDULER_LINE_NAME,
                    "SchedulerLineTypeCode": SCHEDULER_LINE_TYPE,
                    "SchedulerLineOrder": 10,
                    "IsActive": 1,
                }
            )
            _append_edge(result, "Scheduler", scheduler_id, "SchedulerLine", line_id)
            param_id = registry.require(
                "schedulerLineParams", scheduler_line_param_registry_key(periodic_key)
            )
            scheduler_param_rows.append(
                {
                    "SchedulerLineID": line_id,
                    "SchedulerLineParamID": param_id,
                    "SchedulerLineTypeParamCode": SCHEDULER_LINE_PARAM,
                    "SchedulerLineParamValue": str(periodic_id),
                    "IsActive": 1,
                }
            )
            _append_edge(result, "SchedulerLine", line_id, "SchedulerLineParam", param_id)

    if periodic_rows:
        result.rows["Periodic"] = periodic_rows
    if condition_rows:
        result.rows["PeriodicCondition"] = condition_rows
    if action_rows:
        result.rows["PeriodicAction"] = action_rows
    if param_rows:
        result.rows["PeriodicActionParam"] = param_rows
    if action_condition_rows:
        result.rows["PeriodicActionCondition"] = action_condition_rows
    if scheduler_rows:
        result.rows["Scheduler"] = scheduler_rows
    if scheduler_line_rows:
        result.rows["SchedulerLine"] = scheduler_line_rows
    if scheduler_param_rows:
        result.rows["SchedulerLineParam"] = scheduler_param_rows


def _read_conditions(
    index: Any,
    table: str,
    fk_col: str,
    parent_id: int,
    type_col: str,
    param1_col: str,
    param2_col: str,
    id_col: str,
    field_id_to_code: dict[int, str],
    line_field_code,
    explicit: dict[str, Any],
    explicit_category: str,
    registry_key_fn,
) -> list[dict[str, Any]]:
    conditions: list[dict[str, Any]] = []
    for cond in index.rows_for(table, fk_col, parent_id):
        if not _boolish(cond.get("IsActive", 1)):
            continue
        type_slug = condition_slug(int(cond.get(type_col, 0)))
        if not type_slug:
            continue
        line_id = int(cond["ObjectLineID"])
        field_code = line_field_code(index, line_id, field_id_to_code)
        if not field_code:
            continue
        cond_id = int(cond[id_col])
        explicit[explicit_category][registry_key_fn(field_code, type_slug)] = cond_id
        entry: dict[str, Any] = {"field": field_code, "type": type_slug}
        if cond.get(param1_col) is not None:
            entry["param1"] = cond[param1_col]
        if cond.get(param2_col) is not None:
            entry["param2"] = cond[param2_col]
        conditions.append(entry)
    return conditions


def _scheduler_for_periodic(index: Any, periodic_id: int) -> tuple[dict | None, dict | None, dict | None]:
    matches: list[tuple[int, dict, dict, dict]] = []
    for param in index.rows.get("SchedulerLineParam") or []:
        if str(param.get("SchedulerLineTypeParamCode") or "") != SCHEDULER_LINE_PARAM:
            continue
        if not _boolish(param.get("IsActive", 1)):
            continue
        if str(param.get("SchedulerLineParamValue") or "").strip() != str(periodic_id):
            continue
        line = index.row_by_id("SchedulerLine", int(param["SchedulerLineID"]))
        if not line or not _boolish(line.get("IsActive", 1)):
            continue
        if str(line.get("SchedulerLineTypeCode") or "") != SCHEDULER_LINE_TYPE:
            continue
        sched = index.row_by_id("Scheduler", int(line["SchedulerID"]))
        if not sched or not _boolish(sched.get("IsActive", 1)):
            continue
        matches.append((int(sched["SchedulerID"]), sched, line, param))
    if not matches:
        return None, None, None
    matches.sort(key=lambda item: item[0])
    _, sched, line, param = matches[0]
    return sched, line, param


def extract_periodics(
    index: Any,
    object_id: int,
    field_id_to_code: dict[int, str],
    line_field_code,
    *,
    role_id_to_key: dict[int, str] | None = None,
    status_id_to_key: dict[int, str] | None = None,
    notification_id_to_key: dict[int, str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = [
        row
        for row in index.rows_for("Periodic", "ObjectID", object_id)
        if _boolish(row.get("IsActive", 1))
    ]
    if not rows:
        return [], {}

    rows.sort(key=lambda r: (str(r.get("PeriodicName") or ""), int(r.get("PeriodicID", 0))))
    used_keys: set[str] = set()
    periodics: list[dict[str, Any]] = []
    explicit: dict[str, Any] = {
        "periodics": {},
        "periodicConditions": {},
        "periodicActions": {},
        "periodicActionParams": {},
        "periodicActionConditions": {},
        "schedulers": {},
        "schedulerLines": {},
        "schedulerLineParams": {},
    }

    for row in rows:
        periodic_id = int(row["PeriodicID"])
        base_key = slugify(str(row.get("PeriodicName", f"periodic_{periodic_id}")))
        key = base_key
        n = 2
        while key in used_keys:
            key = f"{base_key}_{n}"
            n += 1
        used_keys.add(key)
        explicit["periodics"][key] = periodic_id

        spec_periodic: dict[str, Any] = {
            "key": key,
            "name": row.get("PeriodicName", key),
            "requestType": request_type_slug(int(row.get("PeriodicRequestTypeID", 0))),
        }

        conditions = _read_conditions(
            index,
            "PeriodicCondition",
            "PeriodicID",
            periodic_id,
            "PeriodicConditionTypeID",
            "PeriodicConditionParam1",
            "PeriodicConditionParam2",
            "PeriodicConditionID",
            field_id_to_code,
            line_field_code,
            explicit,
            "periodicConditions",
            lambda field, typ, pkey=key: condition_registry_key(pkey, field, typ),
        )
        if conditions:
            spec_periodic["conditions"] = conditions

        action_rows = [
            action
            for action in index.rows_for("PeriodicAction", "PeriodicID", periodic_id)
            if _boolish(action.get("IsActive", 1))
        ]
        action_rows.sort(
            key=lambda r: (r.get("PeriodicActionOrder", 10), r.get("PeriodicActionID", 0))
        )
        used_action_keys: set[str] = set()
        actions: list[dict[str, Any]] = []
        for action in action_rows:
            action_id = int(action["PeriodicActionID"])
            action_base = slugify(str(action.get("PeriodicActionName", f"action_{action_id}")))
            action_key = action_base
            n = 2
            while action_key in used_action_keys:
                action_key = f"{action_base}_{n}"
                n += 1
            used_action_keys.add(action_key)
            explicit["periodicActions"][action_registry_key(key, action_key)] = action_id

            spec_action: dict[str, Any] = {
                "key": action_key,
                "name": action.get("PeriodicActionName", action_key),
                "typeCode": action.get("PeriodicActionTypeCode"),
                "order": action.get("PeriodicActionOrder", 10),
            }

            params: dict[str, Any] = {}
            for param in index.rows_for("PeriodicActionParam", "PeriodicActionID", action_id):
                if not _boolish(param.get("IsActive", 1)):
                    continue
                param_code = str(param.get("PeriodicActionTypeParamCode") or "")
                if not param_code:
                    continue
                param_id = int(param["PeriodicActionParamID"])
                explicit["periodicActionParams"][
                    action_param_registry_key(key, action_key, param_code)
                ] = param_id
                params[param_code] = param_spec_value(
                    param_code,
                    param.get("PeriodicActionParamValue"),
                    field_id_to_code,
                    role_id_to_key=role_id_to_key,
                    status_id_to_key=status_id_to_key,
                    notification_id_to_key=notification_id_to_key,
                )
            if params:
                spec_action["params"] = params

            action_conditions = _read_conditions(
                index,
                "PeriodicActionCondition",
                "PeriodicActionID",
                action_id,
                "PeriodicActionConditionTypeID",
                "PeriodicActionConditionParam1",
                "PeriodicActionConditionParam2",
                "PeriodicActionConditionID",
                field_id_to_code,
                line_field_code,
                explicit,
                "periodicActionConditions",
                lambda field, typ, pkey=key, akey=action_key: action_condition_registry_key(
                    pkey, akey, field, typ
                ),
            )
            if action_conditions:
                spec_action["conditions"] = action_conditions
            actions.append(spec_action)
        if actions:
            spec_periodic["actions"] = actions

        sched, line, param = _scheduler_for_periodic(index, periodic_id)
        if sched is not None and line is not None and param is not None:
            cron = sched.get("SchedulerCRON")
            if cron:
                spec_periodic["cron"] = str(cron)
            scheduler_name = str(sched.get("SchedulerName") or "").strip()
            if scheduler_name and scheduler_name != spec_periodic["name"]:
                spec_periodic["schedulerName"] = scheduler_name
            explicit["schedulers"][key] = int(sched["SchedulerID"])
            explicit["schedulerLines"][scheduler_line_registry_key(key)] = int(
                line["SchedulerLineID"]
            )
            explicit["schedulerLineParams"][scheduler_line_param_registry_key(key)] = int(
                param["SchedulerLineParamID"]
            )

        periodics.append(spec_periodic)

    for cat in list(explicit):
        if not explicit[cat]:
            del explicit[cat]
    return periodics, explicit
