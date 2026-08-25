"""Notification spec extract/generate."""

from __future__ import annotations

from typing import Any

from ot_builder.ids import IdRegistry
from ot_builder.object_actions import iter_params
from ot_builder.update_actions import condition_slug, condition_type_id, slugify

NOTIFICATION_ID_PARAM_CODES = frozenset({"NotificationID1", "NotificationID2"})

TYPE_ID_TO_SLUG: dict[int, str] = {1: "single", 2: "summary"}
TYPE_SLUG_TO_ID: dict[str, int] = {
    "single": 1,
    "summary": 2,
    "request_summary": 2,
}

SEND_TO_COLUMNS: tuple[tuple[str, str], ...] = (
    ("requestor", "NotificationEmailRequestor"),
    ("requestorManager", "NotificationEmailRequestorManager"),
    ("owner", "NotificationEmailOwner"),
    ("watch", "NotificationEmailWatch"),
    ("role", "NotificationEmailRole"),
    ("roleManager", "NotificationEmailRoleManager"),
    ("currentUser", "NotificationEmailUser"),
)

WORKFLOW_NOTIFICATION_FIELDS: tuple[tuple[str, str], ...] = (
    ("notification", "NotificationID"),
    ("exportFailNotification", "ExportFailNotificationID"),
    ("recallNotification", "RecallNotificationID"),
    ("failNotification", "WorkflowFailNotificationID"),
)

EXTRA_COLUMNS: tuple[tuple[str, str], ...] = (
    ("to", "NotificationToEmailExtra"),
    ("cc", "NotificationCcEmailExtra"),
    ("bcc", "NotificationBccEmailExtra"),
)


def _boolish(val: Any) -> bool:
    return str(val) in ("1", "True", "true")


def _nid(val: Any) -> int | None:
    if val is None or isinstance(val, bool) or val == "":
        return None
    try:
        n = int(val)
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def type_id(value: Any) -> int:
    if value is None:
        return 1
    if isinstance(value, int):
        if value in TYPE_ID_TO_SLUG:
            return value
        raise ValueError(f"Unknown NotificationTypeID: {value}")
    slug = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    if slug.isdigit():
        return type_id(int(slug))
    if slug not in TYPE_SLUG_TO_ID:
        raise ValueError(f"Unknown notification type: {value!r}")
    return TYPE_SLUG_TO_ID[slug]


def type_slug(type_id_value: int) -> str:
    slug = TYPE_ID_TO_SLUG.get(int(type_id_value))
    if not slug:
        raise ValueError(f"Unknown NotificationTypeID: {type_id_value}")
    return slug


def notification_key(row: dict[str, Any], notification_id: int) -> str:
    name = row.get("NotificationName") if row else None
    return slugify(str(name or f"notification_{notification_id}"))


def condition_registry_key(notif_key: str, field_code: str, type_slug_value: str) -> str:
    return f"{notif_key}/{field_code}/{type_slug_value}"


def attachment_registry_key(notif_key: str, field_code: str, subline_id: int | None = None) -> str:
    if subline_id is not None:
        return f"{notif_key}/{field_code}/sub{subline_id}"
    return f"{notif_key}/{field_code}"


def step_notification_registry_key(step_key: str, notif_key: str) -> str:
    return f"{step_key}/{notif_key}"


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


def require_notification_id(registry: IdRegistry, spec: dict, key: str) -> int:
    notif_key = str(key)
    known = registry.get("notifications", notif_key)
    if known is not None:
        return known
    defined = {
        str(item.get("key") or slugify(str(item.get("name", "notification"))))
        for item in spec.get("notifications") or []
    }
    if notif_key not in defined:
        raise ValueError(
            f"Unknown notification key {notif_key!r} — add it to notifications: "
            "or ids.explicit.notifications"
        )
    return registry.require("notifications", notif_key)


def referenced_notification_keys(spec: dict) -> set[str]:
    keys: set[str] = set()
    wf = spec.get("workflow") or {}
    for spec_field, _column in WORKFLOW_NOTIFICATION_FIELDS:
        val = wf.get(spec_field)
        if val:
            keys.add(str(val))
    for step in wf.get("steps") or []:
        for item in step.get("notifications") or []:
            if isinstance(item, dict):
                if item.get("key"):
                    keys.add(str(item["key"]))
            elif item:
                keys.add(str(item))
        for action in step.get("actions") or []:
            if action.get("notification"):
                keys.add(str(action["notification"]))
    for action in spec.get("objectActions") or []:
        for code, raw in iter_params(action):
            key = _param_notification_key(code, raw)
            if key:
                keys.add(key)
    for periodic in spec.get("periodics") or []:
        for action in periodic.get("actions") or []:
            for code, raw in iter_params(action):
                key = _param_notification_key(code, raw)
                if key:
                    keys.add(key)
    return keys


def _param_notification_key(param_code: str, raw: Any) -> str | None:
    if param_code not in NOTIFICATION_ID_PARAM_CODES:
        return None
    if isinstance(raw, dict) and raw.get("notification"):
        return str(raw["notification"])
    if isinstance(raw, str) and raw and not raw.isdigit():
        return raw
    return None


def collect_notification_ids(index: Any, object_id: int, workflow_id: int | None) -> set[int]:
    ids: set[int] = set()

    def add(val: Any) -> None:
        nid = _nid(val)
        if nid:
            ids.add(nid)

    if workflow_id:
        wf = index.row_by_id("Workflow", workflow_id)
        if wf:
            for _spec_field, column in WORKFLOW_NOTIFICATION_FIELDS:
                add(wf.get(column))
        for step in index.rows_for("WorkflowStep", "WorkflowID", workflow_id):
            step_id = int(step["WorkflowStepID"])
            for row in index.rows_for("WorkflowStepNotification", "WorkflowStepID", step_id):
                if _boolish(row.get("IsActive", 1)):
                    add(row.get("NotificationID"))
            for action in index.rows_for("WorkflowStepAction", "WorkflowStepID", step_id):
                add(action.get("NotificationID"))
    for oa in index.rows_for("ObjectAction", "ObjectID", object_id):
        if not _boolish(oa.get("IsActive", 1)):
            continue
        for param in index.rows_for("ObjectActionParam", "ObjectActionID", int(oa["ObjectActionID"])):
            if str(param.get("ObjectActionTypeParamCode") or "") in NOTIFICATION_ID_PARAM_CODES:
                add(param.get("ObjectActionParamValue"))
    for periodic in index.rows_for("Periodic", "ObjectID", object_id):
        if not _boolish(periodic.get("IsActive", 1)):
            continue
        for action in index.rows_for("PeriodicAction", "PeriodicID", int(periodic["PeriodicID"])):
            for param in index.rows_for(
                "PeriodicActionParam", "PeriodicActionID", int(action["PeriodicActionID"])
            ):
                if str(param.get("PeriodicActionTypeParamCode") or "") in NOTIFICATION_ID_PARAM_CODES:
                    add(param.get("PeriodicActionParamValue"))
    return ids


def extract_notifications(
    index: Any,
    object_id: int,
    workflow_id: int | None,
    field_id_to_code: dict[int, str],
    line_field_code,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[int, str]]:
    wanted = collect_notification_ids(index, object_id, workflow_id)
    if not wanted:
        return [], {}, {}

    rows = []
    for nid in wanted:
        row = index.row_by_id("Notification", nid)
        if row and _boolish(row.get("IsActive", 1)):
            rows.append(row)
    if not rows:
        return [], {}, {}

    rows.sort(key=lambda r: (str(r.get("NotificationName") or ""), int(r.get("NotificationID", 0))))
    used_keys: set[str] = set()
    notifications: list[dict[str, Any]] = []
    explicit: dict[str, Any] = {
        "notifications": {},
        "notificationConditions": {},
        "notificationAttachments": {},
    }
    id_to_key: dict[int, str] = {}

    for row in rows:
        nid = int(row["NotificationID"])
        base_key = notification_key(row, nid)
        key = base_key
        n = 2
        while key in used_keys:
            key = f"{base_key}_{n}"
            n += 1
        used_keys.add(key)
        explicit["notifications"][key] = nid
        id_to_key[nid] = key

        spec_item: dict[str, Any] = {
            "key": key,
            "name": row.get("NotificationName", key),
            "type": type_slug(int(row.get("NotificationTypeID", 1))),
            "subject": str(row.get("NotificationSubject") or ""),
            "format": str(row.get("NotificationFormat") or ""),
        }
        if not _boolish(row.get("IsActive", 1)):
            spec_item["isActive"] = False

        send_to: dict[str, bool] = {}
        for spec_name, column in SEND_TO_COLUMNS:
            if _boolish(row.get(column, 0)):
                send_to[spec_name] = True
        if send_to:
            spec_item["sendTo"] = send_to

        extra: dict[str, str] = {}
        for spec_name, column in EXTRA_COLUMNS:
            val = row.get(column)
            if val is not None and str(val).strip():
                extra[spec_name] = str(val)
        if extra:
            spec_item["extra"] = extra

        from_email = row.get("NotificationFromEmail")
        if from_email is not None and str(from_email).strip():
            spec_item["fromEmail"] = str(from_email)
        compressed = row.get("NotificationCompressedFileName")
        if compressed is not None and str(compressed).strip():
            spec_item["compressedFileName"] = str(compressed)

        conditions: list[dict[str, Any]] = []
        for cond in index.rows_for("NotificationCondition", "NotificationID", nid):
            if not _boolish(cond.get("IsActive", 1)):
                continue
            type_s = condition_slug(int(cond.get("NotificationConditionTypeID", 0)))
            if not type_s:
                continue
            line_id = int(cond["ObjectLineID"])
            field_code = line_field_code(index, line_id, field_id_to_code)
            if not field_code:
                continue
            cond_id = int(cond["NotificationConditionID"])
            explicit["notificationConditions"][condition_registry_key(key, field_code, type_s)] = (
                cond_id
            )
            entry: dict[str, Any] = {"field": field_code, "type": type_s}
            if cond.get("NotificationConditionParam1") is not None:
                entry["param1"] = cond["NotificationConditionParam1"]
            if cond.get("NotificationConditionParam2") is not None:
                entry["param2"] = cond["NotificationConditionParam2"]
            conditions.append(entry)
        if conditions:
            spec_item["conditions"] = conditions

        attachments: list[dict[str, Any]] = []
        for att in index.rows_for("NotificationAttachment", "NotificationID", nid):
            if not _boolish(att.get("IsActive", 1)):
                continue
            line_id = int(att["ObjectLineID"])
            field_code = line_field_code(index, line_id, field_id_to_code)
            if not field_code:
                continue
            subline_id = _nid(att.get("ObjectSubLineID"))
            att_id = int(att["NotificationAttachmentID"])
            explicit["notificationAttachments"][
                attachment_registry_key(key, field_code, subline_id)
            ] = att_id
            entry = {"field": field_code}
            if not _boolish(att.get("NotificationAttachmentIsCompressed", 1)):
                entry["compressed"] = False
            if subline_id is not None:
                entry["sublineId"] = subline_id
            attachments.append(entry)
        if attachments:
            spec_item["attachments"] = attachments

        notifications.append(spec_item)

    for cat in list(explicit):
        if not explicit[cat]:
            del explicit[cat]
    return notifications, explicit, id_to_key


def build_notifications(spec: dict, registry: IdRegistry, result: Any) -> None:
    notifications = spec.get("notifications") or []
    if not notifications:
        referenced = referenced_notification_keys(spec)
        if referenced:
            missing = [
                key
                for key in referenced
                if registry.get("notifications", key) is None
            ]
            if missing:
                raise ValueError(
                    "Unknown notification key(s) "
                    + ", ".join(repr(k) for k in missing)
                    + " — add them to notifications: or ids.explicit.notifications"
                )
        return

    referenced = referenced_notification_keys(spec)
    defined_keys: list[str] = []
    notification_rows: list[dict] = []
    condition_rows: list[dict] = []
    attachment_rows: list[dict] = []

    for item in notifications:
        key = str(item.get("key") or slugify(str(item.get("name", "notification"))))
        defined_keys.append(key)
        if key not in referenced:
            raise ValueError(
                f"notifications.{key} is not bound to workflow, a step action, "
                "ObjectAction, or PeriodicAction"
            )
        nid = registry.require("notifications", key)
        subject = str(item.get("subject") or "").strip()
        body = str(item.get("format") or "").strip()
        if not subject:
            raise ValueError(f"notifications.{key}: subject is required")
        if not body:
            raise ValueError(f"notifications.{key}: format is required")
        row: dict[str, Any] = {
            "NotificationID": nid,
            "NotificationName": item.get("name", key),
            "NotificationTypeID": type_id(item.get("type")),
            "NotificationSubject": subject,
            "NotificationFormat": body,
            "IsActive": 1 if item.get("isActive", True) else 0,
        }
        send_to = item.get("sendTo") or {}
        for spec_name, column in SEND_TO_COLUMNS:
            row[column] = 1 if send_to.get(spec_name) else 0
        extra = item.get("extra") or {}
        for spec_name, column in EXTRA_COLUMNS:
            val = extra.get(spec_name)
            if val is not None and str(val).strip():
                row[column] = str(val)
        if item.get("fromEmail"):
            row["NotificationFromEmail"] = str(item["fromEmail"])
        if item.get("compressedFileName"):
            row["NotificationCompressedFileName"] = str(item["compressedFileName"])
        notification_rows.append(row)

        for cond in item.get("conditions") or []:
            field_code = str(cond["field"])
            type_s = str(cond["type"])
            cond_id = registry.require(
                "notificationConditions",
                condition_registry_key(key, field_code, type_s),
            )
            condition_rows.append(
                {
                    "NotificationConditionID": cond_id,
                    "NotificationID": nid,
                    "ObjectLineID": registry.require("fields", field_code),
                    "NotificationConditionTypeID": condition_type_id(type_s),
                    "NotificationConditionParam1": cond.get("param1"),
                    "NotificationConditionParam2": cond.get("param2"),
                    "IsActive": 1 if cond.get("isActive", True) else 0,
                }
            )
            _append_edge(result, "Notification", nid, "NotificationCondition", cond_id)

        for att in item.get("attachments") or []:
            field_code = str(att["field"])
            subline_id = att.get("sublineId")
            att_id = registry.require(
                "notificationAttachments",
                attachment_registry_key(key, field_code, subline_id),
            )
            att_row: dict[str, Any] = {
                "NotificationAttachmentID": att_id,
                "NotificationID": nid,
                "ObjectLineID": registry.require("fields", field_code),
                "NotificationAttachmentIsCompressed": 0 if att.get("compressed") is False else 1,
                "IsActive": 1,
            }
            if subline_id is not None:
                att_row["ObjectSubLineID"] = int(subline_id)
            attachment_rows.append(att_row)
            _append_edge(result, "Notification", nid, "NotificationAttachment", att_id)

    missing = [key for key in referenced if key not in defined_keys and registry.get("notifications", key) is None]
    if missing:
        raise ValueError(
            "Unknown notification key(s) "
            + ", ".join(repr(k) for k in missing)
            + " — add them to notifications: or ids.explicit.notifications"
        )

    if notification_rows:
        result.rows["Notification"] = notification_rows
    if condition_rows:
        result.rows["NotificationCondition"] = condition_rows
    if attachment_rows:
        result.rows["NotificationAttachment"] = attachment_rows
