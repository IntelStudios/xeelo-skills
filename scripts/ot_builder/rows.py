"""Build table rows and hierarchy metadata from xeelo-spec."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from ot_builder.ids import IdRegistry, build_registry
from ot_builder.language_table import emit_language_table
from ot_builder.ongrid import require_ongrid_id
from ot_builder.reopen import reopen_on_save_id
from ot_builder.object_actions import (
    condition_registry_key,
    iter_params,
    param_registry_key,
    resolve_param_value,
    step_link_registry_key,
)
from ot_builder.object_messages import (
    HTML_DB_COLUMN,
    condition_registry_key as object_message_condition_registry_key,
    style_id as object_message_style_id,
)
from ot_builder.spec_loader import normalize_spec, spec_references
from ot_builder.templates import (
    COMBO_FIELD_TYPES,
    LOOKUP_FIELD_TYPES,
    REFERENCE_FIELD_TYPES,
    apply_template_line_extras,
    apply_template_line_validation,
    is_legacy_single_template,
    iter_layout_fields,
    iter_templates,
    require_template_line_id,
    resolve_template_id,
    template_access_registry_key,
)
from ot_builder.update_actions import (
    access_registry_key,
    condition_type_id,
    resolve_access_flags,
    require_workflow_step_action_id,
    slugify,
    step_access_registry_key,
    workflow_step_key,
)

DATA = Path(__file__).resolve().parent.parent.parent / "data"

MINIMAL_ROLE_KEYS = ("requestor", "owner")
MINIMAL_STATUS_KEYS = ("draft", "active", "completed")

DEFAULT_ROLES: dict[str, dict[str, Any]] = {
    "requestor": {"name": "Requestor", "isRequestor": True},
    "owner": {"name": "Owner", "isOwner": True},
}

DEFAULT_STATUSES: dict[str, dict[str, Any]] = {
    "draft": {"name": "Draft", "order": 10},
    "active": {"name": "Active", "order": 20},
    "completed": {"name": "Completed", "isCompleted": True, "order": 30},
}


def load_field_mapping() -> dict:
    return json.loads((DATA / "field-type-mapping.json").read_text(encoding="utf-8"))


def _set_optional_int(row: dict[str, Any], column: str, value: Any) -> None:
    if value is not None:
        row[column] = int(value)


def _set_optional_bool(row: dict[str, Any], column: str, value: Any) -> None:
    if value is not None:
        row[column] = 1 if value else 0


def _set_optional_str(row: dict[str, Any], column: str, value: Any) -> None:
    if value is not None:
        row[column] = str(value)


def _set_optional_nonempty(row: dict[str, Any], column: str, value: Any) -> None:
    if value is None:
        return
    text = str(value).strip()
    if text:
        row[column] = text


def _apply_object_line_extras(
    line_row: dict[str, Any],
    field: dict[str, Any],
    ftype: str,
    registry: IdRegistry,
) -> None:
    if field.get("uniqueId") is not None:
        line_row["ObjectLineUniqueID"] = int(field["uniqueId"])
        line_row["ObjectLineIsUnique"] = 1

    if ftype == "number":
        _set_optional_str(line_row, "ObjectLineNumberSeparator", field.get("numberSeparator"))
        _set_optional_int(line_row, "ObjectLineNumberMin", field.get("numberMin"))
        _set_optional_int(line_row, "ObjectLineNumberMax", field.get("numberMax"))
    if ftype == "text":
        _set_optional_int(line_row, "ObjectLineTextInputType", field.get("textInputType"))
    if ftype in ("radio", "checkbox_multiselect"):
        _set_optional_int(line_row, "ObjectLineNumberColumns", field.get("columnNumbers"))
    if ftype == "web_frame":
        _set_optional_int(line_row, "WebFrameTypeID", field.get("webFrameTypeId"))
    if ftype in ("memo", "report"):
        _set_optional_int(line_row, "ObjectLineHeight", field.get("height"))
    if ftype == "description_memo":
        _set_optional_bool(line_row, "ObjectLineDescMemoIsBorder", field.get("descMemoBorder"))
        _set_optional_int(line_row, "ObjectLineDescMemoPadding", field.get("descMemoPadding"))
    if ftype == "button":
        _set_optional_str(line_row, "ObjectLineButtonMessage", field.get("buttonMessage"))
        _set_optional_str(line_row, "ObjectLineColorFont", field.get("colorFont"))
        _set_optional_str(line_row, "ObjectLineColorBack", field.get("colorBack"))
    if ftype in COMBO_FIELD_TYPES:
        _set_optional_bool(line_row, "ObjectLineIsReferenceLink", field.get("isReferenceLink"))
    if ftype == "attachment":
        _set_optional_int(line_row, "AttachmentStorageID", field.get("attachmentStorageId"))
        _set_optional_bool(line_row, "ObjectLineAttachmentIsOCR", field.get("ocr"))
        _set_optional_str(line_row, "ObjectLineAttachmentOCRLang", field.get("ocrLang"))
        _set_optional_int(line_row, "ObjectLineAttachmentImageResizeMax", field.get("imageResizeMax"))
        _set_optional_bool(line_row, "ObjectLineAttachmentMobileIsScan", field.get("mobileScan"))
        _set_optional_bool(
            line_row, "ObjectLineAttachmentMobileIsSignature", field.get("mobileSignature")
        )
    if ftype == "attachment_preview":
        preview_field = field.get("previewField")
        if preview_field:
            line_row["ObjectLineAttPreviewObjectLineID"] = registry.require(
                "fields", str(preview_field)
            )
        _set_optional_bool(line_row, "ObjectLineAttPreviewIsDownload", field.get("previewDownload"))


def validate_spec(spec: dict) -> None:
    if spec.get("version") != 2:
        raise ValueError("xeelo-spec requires version: 2")
    tabs = spec.get("layout", {}).get("tabs")
    if not tabs:
        raise ValueError("xeelo-spec requires layout.tabs with at least one tab")


def _roles_map(spec: dict) -> dict[str, dict]:
    roles = dict(spec.get("roles") or {})
    if not roles:
        roles = dict(DEFAULT_ROLES)
    return roles


def _statuses_map(spec: dict) -> dict[str, dict]:
    statuses = dict(spec.get("statuses") or {})
    if not statuses:
        statuses = dict(DEFAULT_STATUSES)
    return statuses


def _resolve_role_id(spec: dict, registry: IdRegistry, key: str) -> int:
    if key not in _roles_map(spec):
        raise ValueError(f"Unknown role key: {key!r}")
    return registry.require("roles", key)


def _resolve_status_id(spec: dict, registry: IdRegistry, key: str) -> int:
    if key not in _statuses_map(spec):
        raise ValueError(f"Unknown status key: {key!r}")
    return registry.require("statuses", key)


class BuildResult:
    def __init__(self) -> None:
        self.rows: dict[str, list[dict]] = {}
        self.edges: list[dict] = []
        self.field_meta: dict[str, dict] = {}
        self.used_role_keys: set[str] = set()
        self.used_status_keys: set[str] = set()


def _track_role_status(
    spec: dict,
    registry: IdRegistry,
    result: BuildResult,
    role_key: str,
    status_key: str,
) -> tuple[int, int]:
    result.used_role_keys.add(role_key)
    result.used_status_keys.add(status_key)
    return (
        _resolve_role_id(spec, registry, role_key),
        _resolve_status_id(spec, registry, status_key),
    )


def _add_wf_role_status_edges(result: BuildResult, wf_id: int, role_id: int, status_id: int) -> None:
    result.edges.extend(
        [
            {
                "TableName": "Workflow",
                "TableRowID": wf_id,
                "ChildTableName": "Role",
                "ChildTableRowID": role_id,
            },
            {
                "TableName": "Workflow",
                "TableRowID": wf_id,
                "ChildTableName": "RequestStatus",
                "ChildTableRowID": status_id,
            },
        ]
    )


def _add_step_role_status_edges(result: BuildResult, step_id: int, role_id: int, status_id: int) -> None:
    result.edges.extend(
        [
            {
                "TableName": "WorkflowStep",
                "TableRowID": step_id,
                "ChildTableName": "Role",
                "ChildTableRowID": role_id,
            },
            {
                "TableName": "WorkflowStep",
                "TableRowID": step_id,
                "ChildTableName": "RequestStatus",
                "ChildTableRowID": status_id,
            },
        ]
    )


REQUEST_TYPE_IDS = {"all": 0, "completed": 1, "in-progress": 2, "inprogress": 2}

REF_OBJECT_LINE_COLUMNS = {
    "value": "ValueObjectLineID",
    "valueName": "ValueNameObjectLineID",
    "valueBind": "ValueBindObjectLineID",
    "valueFilter": "ValueFilterObjectLineID",
    "valueOrder": "ValueOrderObjectLineID",
}


def _resolve_ref_object_line_id(spec: dict, registry: IdRegistry, code_or_id: str | int) -> int:
    if isinstance(code_or_id, int):
        return code_or_id
    text = str(code_or_id)
    if text.isdigit():
        return int(text)
    explicit = (spec.get("ids") or {}).get("explicit") or {}
    ref_lines = explicit.get("refObjectLines") or {}
    if text in ref_lines:
        return int(ref_lines[text])
    fields = explicit.get("fields") or {}
    if text in fields:
        return int(fields[text])
    by_table = (spec.get("ids") or {}).get("byTable") or {}
    for row_id, line_id in (by_table.get("ObjectLine") or {}).items():
        if str(row_id) == text:
            return int(line_id)
    raise ValueError(f"Cannot resolve refObject line reference: {text!r}")


def _resolve_source_id(spec: dict, registry: IdRegistry, reference: dict) -> int:
    if reference.get("referenceId") is not None:
        return int(reference["referenceId"])
    if reference.get("sourceId") is not None:
        return int(reference["sourceId"])
    source_key = reference.get("reference") or reference.get("source")
    if not source_key:
        raise ValueError("reference requires referenceId or reference")
    references = spec_references(spec)
    if source_key not in references:
        raise ValueError(f"Unknown reference key: {source_key!r}")
    return registry.require("references", str(source_key))


def _emit_sources(spec: dict, registry: IdRegistry, result: BuildResult) -> None:
    sources = spec_references(spec)
    if not sources:
        return

    source_rows: list[dict] = []
    value_rows: list[dict] = []
    ref_object_rows: list[dict] = []

    for key in sorted(sources.keys()):
        source_def = sources[key]
        source_id = registry.require("references", key)
        source_row: dict[str, Any] = {
            "ObjectLineSourceID": source_id,
            "ObjectLineSourceName": source_def["name"],
            "ObjectLineSourceTypeID": int(source_def["typeId"]),
            "ObjectLineSourceStyleID": int(source_def.get("styleId", 4)),
            "IsActive": 1,
        }
        source_rows.append(source_row)

        if source_def.get("values"):
            for index, value_def in enumerate(source_def["values"]):
                value_key = str(value_def["value"])
                value_id = registry.require("sourceValues", value_key)
                value_rows.append(
                    {
                        "ObjectLineSourceValueID": value_id,
                        "ObjectLineSourceID": source_id,
                        "ObjectLineSourceValue": value_def["value"],
                        "ObjectLineSourceValueName": value_def["label"],
                        "ObjectLineSourceValueBind": value_def.get("bind", value_def["value"]),
                        "ObjectLineSourceValueOrder": value_def.get("order", index),
                        "IsActive": 1,
                    }
                )
                result.edges.append(
                    {
                        "TableName": "ObjectLineSource",
                        "TableRowID": source_id,
                        "ChildTableName": "ObjectLineSourceValue",
                        "ChildTableRowID": value_id,
                    }
                )

        ref_object = source_def.get("refObject")
        if ref_object:
            ref_id = registry.require("sourceRefObjects", key)
            ref_row: dict[str, Any] = {
                "ObjectLineSourceRefObjectID": ref_id,
                "ObjectLineSourceRefObjectName": ref_object.get("name", source_def["name"]),
                "ObjectLineSourceID": source_id,
                "ObjectID": int(ref_object["objectId"]),
                "ObjectLineSourceRefObjectRequestTypeID": REQUEST_TYPE_IDS.get(
                    ref_object.get("requestType", "all"), 0
                ),
                # Draft/Open accounts must appear; SQL default IsOnlyCompleted=1 would hide them.
                "ObjectLineSourceRefObjectIsOnlyCompleted": 1
                if ref_object.get("requestType") == "completed"
                else 0,
                "IsActive": 1,
            }
            for role, column in REF_OBJECT_LINE_COLUMNS.items():
                line_ref = (ref_object.get("lines") or {}).get(role)
                if line_ref:
                    ref_row[column] = _resolve_ref_object_line_id(spec, registry, line_ref)
            ref_object_rows.append(ref_row)
            result.edges.append(
                {
                    "TableName": "ObjectLineSource",
                    "TableRowID": source_id,
                    "ChildTableName": "ObjectLineSourceRefObject",
                    "ChildTableRowID": ref_id,
                }
            )

    if source_rows:
        result.rows["ObjectLineSource"] = source_rows
    if value_rows:
        result.rows["ObjectLineSourceValue"] = value_rows
    if ref_object_rows:
        result.rows["ObjectLineSourceRefObject"] = ref_object_rows


def _lookup_value_parts(value: dict) -> tuple[str, str, str | None, str | None]:
    ret = str(value.get("return", value.get("value", "")))
    source = str(value.get("source", value.get("label", ret)))
    filt = value.get("filter")
    filt_s = str(filt) if filt not in (None, "") else None
    source_to = value.get("sourceTo")
    source_to_s = str(source_to) if source_to not in (None, "") else None
    return source, ret, filt_s, source_to_s


def _field_lookup_key(field: dict, lookup: dict) -> str:
    key = lookup.get("lookup")
    if key:
        return str(key)
    name = lookup.get("name") or field.get("name") or "lookup"
    return slugify(str(name)) or "lookup"


def _collect_lookup_defs(spec: dict) -> dict[str, dict]:
    defs = dict(spec.get("lookups") or {})
    for field in iter_layout_fields(spec):
        lookup = field.get("lookup")
        if not isinstance(lookup, dict):
            continue
        key = lookup.get("lookup")
        if key:
            if str(key) not in defs:
                raise ValueError(f"Unknown lookup key: {key!r}")
            continue
        values = lookup.get("values")
        if not values:
            raise ValueError(
                f"Field {field.get('code')!r} lookup requires lookup key or values"
            )
        name = lookup.get("name") or field.get("name") or "lookup"
        inline_key = slugify(str(name)) or "lookup"
        if inline_key not in defs:
            entry: dict[str, Any] = {"name": name, "values": values}
            if lookup.get("matchId") is not None:
                entry["matchId"] = lookup["matchId"]
            defs[inline_key] = entry
    return defs


def _emit_lookups(spec: dict, registry: IdRegistry, result: BuildResult) -> None:
    defs = _collect_lookup_defs(spec)
    if not defs:
        return

    lookup_rows: list[dict] = []
    lookup_value_rows: list[dict] = []
    for key in sorted(defs.keys()):
        lookup_def = defs[key]
        lookup_id = registry.require("lookups", key)
        lookup_rows.append(
            {
                "ObjectLineLookupID": lookup_id,
                "ObjectLineLookupName": lookup_def.get("name", key),
                "ObjectLineLookupMatchID": int(lookup_def.get("matchId", 1)),
                "ObjectLineLookupIsCache": 1,
                "IsActive": 1,
            }
        )
        for value in lookup_def.get("values") or []:
            source, ret, filt, source_to = _lookup_value_parts(value)
            value_key = f"{key}|{source}|{filt or ''}|{ret}"
            lv_id = registry.require("lookupValues", value_key)
            row: dict[str, Any] = {
                "ObjectLineLookupValueID": lv_id,
                "ObjectLineLookupID": lookup_id,
                "ObjectLineLookupSourceValue": source,
                "ObjectLineLookupReturnValue": ret,
                "IsActive": 1,
            }
            if source_to is not None:
                row["ObjectLineLookupSourceValue1"] = source_to
            if filt is not None:
                row["ObjectLineLookupFilterValue"] = filt
            lookup_value_rows.append(row)
            result.edges.append(
                {
                    "TableName": "ObjectLineLookup",
                    "TableRowID": lookup_id,
                    "ChildTableName": "ObjectLineLookupValue",
                    "ChildTableRowID": lv_id,
                }
            )

    if lookup_rows:
        result.rows["ObjectLineLookup"] = lookup_rows
    if lookup_value_rows:
        result.rows["ObjectLineLookupValue"] = lookup_value_rows


def _collect_autonumber_defs(spec: dict) -> dict[str, dict]:
    defs = dict(spec.get("autonumbers") or {})
    used: set[str] = set()
    for field in iter_layout_fields(spec):
        key = field.get("autonumber")
        if key:
            used.add(str(key))
    for template_cfg in iter_templates(spec):
        for field_cfg in (template_cfg.get("fields") or {}).values():
            if isinstance(field_cfg, dict) and field_cfg.get("autonumber"):
                used.add(str(field_cfg["autonumber"]))
    for key in used:
        if key not in defs:
            raise ValueError(f"Unknown autonumber key: {key!r}")
    return defs


def _emit_autonumbers(spec: dict, registry: IdRegistry, result: BuildResult) -> None:
    defs = _collect_autonumber_defs(spec)
    if not defs:
        return

    rows: list[dict] = []
    for key in sorted(defs.keys()):
        autonumber_def = defs[key]
        if not autonumber_def.get("format"):
            raise ValueError(f"autonumber {key!r} requires format")
        autonumber_id = registry.require("autonumbers", key)
        row: dict[str, Any] = {
            "ObjectLineAutoNumberID": autonumber_id,
            "ObjectLineAutoNumberDescription": autonumber_def.get("description", key),
            "ObjectLineAutoNumberFormat": str(autonumber_def["format"]),
            "ObjectLineAutoNumberNext": int(autonumber_def.get("next", 1)),
            "IsActive": 1,
        }
        reset_type = autonumber_def.get("resetTypeId")
        if reset_type is not None:
            row["ObjectLineAutoNumberResetTypeID"] = int(reset_type)
        rows.append(row)
    result.rows["ObjectLineAutoNumber"] = rows


def _section_key(tab_name: str, section_name: str) -> str:
    return f"{tab_name}/{section_name}"


def _emit_roles_and_statuses(spec: dict, registry: IdRegistry, result: BuildResult) -> None:
    roles = _roles_map(spec)
    statuses = _statuses_map(spec)

    role_rows = []
    for key in sorted(result.used_role_keys):
        role_def = roles[key]
        role_id = registry.require("roles", key)
        role_rows.append(
            {
                "RoleID": role_id,
                "RoleName": role_def["name"],
                "IsRequestor": 1 if role_def.get("isRequestor") else 0,
                "IsOwner": 1 if role_def.get("isOwner") else 0,
                "IsActive": 1 if role_def.get("isActive", True) else 0,
            }
        )

    status_rows = []
    for key in sorted(result.used_status_keys):
        status_def = statuses[key]
        status_id = registry.require("statuses", key)
        status_rows.append(
            {
                "RequestStatusID": status_id,
                "RequestStatusName": status_def["name"],
                "RequestStatusIsCompleted": 1 if status_def.get("isCompleted") else 0,
                "RequestStatusIsCanceled": 1 if status_def.get("isCanceled") else 0,
                "RequestStatusOrder": status_def.get("order", 10),
                "IsActive": 1 if status_def.get("isActive", True) else 0,
            }
        )

    if role_rows:
        result.rows["Role"] = role_rows
    if status_rows:
        result.rows["RequestStatus"] = status_rows


def _workflow_reused(spec: dict) -> bool:
    """True when the object binds an existing Workflow Orig. ID (do not upsert WF definition)."""
    return bool((spec.get("workflow") or {}).get("reuse"))


def _emit_workflow_step_access(
    spec: dict, registry: IdRegistry, result: BuildResult, steps: list
) -> None:
    """Per-(step, line) access for this object's fields. Safe when the Workflow already exists."""
    for step in steps:
        step_key = workflow_step_key(step)
        step_id = registry.require("workflowSteps", step_key)
        for access in step.get("access") or []:
            field_code = str(access["field"])
            subline_id = access.get("sublineId")
            reg_key = step_access_registry_key(step_key, field_code, subline_id)
            access_id = registry.require("workflowStepAccess", reg_key)
            editable_bit, visible_bit = resolve_access_flags(access)
            access_row: dict[str, Any] = {
                "WorkflowStepID": step_id,
                "WorkflowStepAccessID": access_id,
                "ObjectLineID": registry.require("fields", field_code),
                "WorkflowStepAccessIsEditable": editable_bit,
                "WorkflowStepAccessIsVisible": visible_bit,
                "IsActive": 1,
            }
            if subline_id is not None:
                access_row["ObjectSubLineID"] = int(subline_id)
            result.rows.setdefault("WorkflowStepAccess", []).append(access_row)
            result.edges.append(
                {
                    "TableName": "WorkflowStep",
                    "TableRowID": step_id,
                    "ChildTableName": "WorkflowStepAccess",
                    "ChildTableRowID": access_id,
                }
            )


def _build_workflow_full(spec: dict, registry: IdRegistry, oid: int, result: BuildResult) -> int:
    wf = spec["workflow"]
    wf_id = registry.require_scalar("workflowId")
    if _workflow_reused(spec):
        _emit_workflow_step_access(spec, registry, result, wf.get("steps") or [])
        return wf_id

    wf_name = wf.get("name") or f"{spec['object']['name']} Workflow"
    first_step = wf["steps"][0]
    first_role_id, first_status_id = _track_role_status(
        spec, registry, result, first_step["role"], first_step["status"]
    )
    result.rows["Workflow"] = [
        {
            "WorkflowID": wf_id,
            "WorkflowName": wf_name,
            "RoleID": first_role_id,
            "RequestStatusID": first_status_id,
            "IsActive": 1,
        }
    ]
    result.edges.append(
        {"TableName": "Object", "TableRowID": oid, "ChildTableName": "Workflow", "ChildTableRowID": wf_id}
    )
    _add_wf_role_status_edges(result, wf_id, first_role_id, first_status_id)

    for step in wf.get("steps", []):
        step_name = step["name"]
        step_key = workflow_step_key(step)
        step_id = registry.require("workflowSteps", step_key)
        role_id, status_id = _track_role_status(spec, registry, result, step["role"], step["status"])
        result.rows.setdefault("WorkflowStep", []).append(
            {
                "WorkflowStepID": step_id,
                "WorkflowID": wf_id,
                "WorkflowStepName": step_name,
                "RoleID": role_id,
                "RequestStatusID": status_id,
                "WorkflowStepIsSuppressSave": 1 if step.get("suppressSave") else 0,
                "IsActive": 1 if step.get("isActive", True) else 0,
            }
        )
        result.edges.append(
            {
                "TableName": "Workflow",
                "TableRowID": wf_id,
                "ChildTableName": "WorkflowStep",
                "ChildTableRowID": step_id,
            }
        )
        _add_step_role_status_edges(result, step_id, role_id, status_id)

        for action in step.get("actions", []):
            action_name = action["name"]
            action_id = require_workflow_step_action_id(registry, action)
            action_role_id, action_status_id = _track_role_status(
                spec, registry, result, action["role"], action["status"]
            )
            style_id = action.get("styleId", 1)
            action_row: dict[str, Any] = {
                "WorkflowStepActionID": action_id,
                "WorkflowStepID": step_id,
                "WorkflowStepActionName": action_name,
                "WorkflowStepActionOrder": action.get("order", 10),
                "RoleID": action_role_id,
                "RequestStatusID": action_status_id,
                "WorkflowStepActionStyleID": style_id,
                "IsActive": 1 if action.get("isActive", True) else 0,
            }
            reopen_id = reopen_on_save_id(action.get("reopenOnSave"))
            if reopen_id is not None:
                action_row["WorkflowStepActionReopenTypeID"] = reopen_id
            result.rows.setdefault("WorkflowStepAction", []).append(action_row)
            result.edges.extend(
                [
                    {
                        "TableName": "WorkflowStep",
                        "TableRowID": step_id,
                        "ChildTableName": "WorkflowStepAction",
                        "ChildTableRowID": action_id,
                    },
                    {
                        "TableName": "WorkflowStepAction",
                        "TableRowID": action_id,
                        "ChildTableName": "WorkflowStepActionStyle",
                        "ChildTableRowID": style_id,
                    },
                ]
            )

    _emit_workflow_step_access(spec, registry, result, wf.get("steps") or [])
    return wf_id


def _build_workflow_minimal(spec: dict, registry: IdRegistry, oid: int, result: BuildResult) -> int:
    obj = spec["object"]
    wf_id = registry.require_scalar("workflowId")
    wf_name = spec.get("workflow", {}).get("name") or f"{obj['name']} Workflow"

    requestor_id, draft_id = _track_role_status(spec, registry, result, "requestor", "draft")
    owner_id, active_id = _track_role_status(spec, registry, result, "owner", "active")
    _, completed_id = _track_role_status(spec, registry, result, "requestor", "completed")

    result.rows["Workflow"] = [
        {
            "WorkflowID": wf_id,
            "WorkflowName": wf_name,
            "RoleID": requestor_id,
            "RequestStatusID": draft_id,
            "IsActive": 1,
        }
    ]
    result.edges.append(
        {"TableName": "Object", "TableRowID": oid, "ChildTableName": "Workflow", "ChildTableRowID": wf_id}
    )
    _add_wf_role_status_edges(result, wf_id, requestor_id, draft_id)

    step_draft = registry.require("workflowSteps", "Draft")
    step_active = registry.require("workflowSteps", "Active")
    result.rows["WorkflowStep"] = [
        {
            "WorkflowStepID": step_draft,
            "WorkflowID": wf_id,
            "WorkflowStepName": "Draft",
            "RoleID": requestor_id,
            "RequestStatusID": draft_id,
            "IsActive": 1,
        },
        {
            "WorkflowStepID": step_active,
            "WorkflowID": wf_id,
            "WorkflowStepName": "Active",
            "RoleID": owner_id,
            "RequestStatusID": active_id,
            "IsActive": 1,
        },
    ]
    for step_id, role_id, status_id in (
        (step_draft, requestor_id, draft_id),
        (step_active, owner_id, active_id),
    ):
        result.edges.append(
            {
                "TableName": "Workflow",
                "TableRowID": wf_id,
                "ChildTableName": "WorkflowStep",
                "ChildTableRowID": step_id,
            }
        )
        _add_step_role_status_edges(result, step_id, role_id, status_id)

    action_submit = registry.require("workflowStepActions", "Submit")
    action_complete = registry.require("workflowStepActions", "Complete")
    result.rows["WorkflowStepAction"] = [
        {
            "WorkflowStepActionID": action_submit,
            "WorkflowStepID": step_draft,
            "WorkflowStepActionName": "Submit",
            "WorkflowStepActionOrder": 10,
            "RoleID": owner_id,
            "RequestStatusID": active_id,
            "WorkflowStepActionStyleID": 1,
            "IsActive": 1,
        },
        {
            "WorkflowStepActionID": action_complete,
            "WorkflowStepID": step_active,
            "WorkflowStepActionName": "Complete",
            "WorkflowStepActionOrder": 10,
            "RoleID": requestor_id,
            "RequestStatusID": completed_id,
            "WorkflowStepActionStyleID": 1,
            "IsActive": 1,
        },
    ]
    result.edges.extend(
        [
            {
                "TableName": "WorkflowStep",
                "TableRowID": step_draft,
                "ChildTableName": "WorkflowStepAction",
                "ChildTableRowID": action_submit,
            },
            {
                "TableName": "WorkflowStepAction",
                "TableRowID": action_submit,
                "ChildTableName": "WorkflowStepActionStyle",
                "ChildTableRowID": 1,
            },
            {
                "TableName": "WorkflowStep",
                "TableRowID": step_active,
                "ChildTableName": "WorkflowStepAction",
                "ChildTableRowID": action_complete,
            },
            {
                "TableName": "WorkflowStepAction",
                "TableRowID": action_complete,
                "ChildTableName": "WorkflowStepActionStyle",
                "ChildTableRowID": 1,
            },
        ]
    )
    return wf_id


def _object_default_row(
    spec: dict,
    *,
    template_id: int,
    object_id: int,
    workflow_id: int,
    template_cfg: dict[str, Any],
    template_key: str,
    is_default: bool,
) -> dict[str, Any]:
    explicit = (spec.get("ids") or {}).get("explicit") or {}
    links = explicit.get("objectDefaultExternalLinks") or {}

    external_link = (
        template_cfg.get("externalLink")
        or links.get(template_key)
        or (explicit.get("objectDefaultExternalLink") if is_default else None)
        or str(uuid.uuid4()).upper()
    )
    access_owner_level = template_cfg.get(
        "accessOwnerLevel",
        explicit.get("objectDefaultAccessOwnerLevel", 0) if is_default else 0,
    )
    is_external = template_cfg.get(
        "isExternal",
        explicit.get("objectDefaultIsExternal", 0) if is_default else 0,
    )

    row: dict[str, Any] = {
        "ObjectDefaultID": template_id,
        "ObjectID": object_id,
        "ObjectDefaultName": template_cfg.get("name", "Default"),
        "ObjectDefaultOrder": template_cfg.get("order", 0),
        "WorkflowID": workflow_id,
        "ObjectDefaultIsDefault": 1 if is_default else 0,
        "ObjectDefaultAccessOwnerLevel": int(access_owner_level),
        "ObjectDefaultIsExternal": int(is_external),
        "ObjectDefaultExternalLink": str(external_link).upper(),
        "IsActive": 1,
    }
    reopen_id = reopen_on_save_id(template_cfg.get("reopenOnSave"))
    if reopen_id is not None:
        row["ObjectDefaultReopenTypeID"] = reopen_id
    return row


def _tab_id_for_name(spec: dict, registry: IdRegistry, tab_name: str | None, *, placement: int) -> int | None:
    if not tab_name:
        return None
    tabs = (spec.get("layout") or {}).get("tabs") or []
    for tab in tabs:
        if tab.get("name") == tab_name and int(tab.get("placement", 0)) == placement:
            section = (tab.get("sections") or [{}])[0]
            section_name = section.get("name", tab_name)
            tab_key = f"{tab_name}/{section_name}"
            return registry.optional("tabs", tab_key)
    return None


def _build_object_messages(spec: dict, registry: IdRegistry, oid: int, result: BuildResult) -> None:
    messages = spec.get("objectMessages") or []
    if not messages:
        return

    message_rows: list[dict] = []
    condition_rows: list[dict] = []

    for msg in messages:
        msg_key = str(msg.get("key") or slugify(str(msg.get("name", "message"))))
        message_id = registry.require("objectMessages", msg_key)
        html = str(msg.get("html") or "").strip()
        if not html:
            raise ValueError(f"objectMessages.{msg_key}: html is required")
        style = object_message_style_id(msg.get("styleId", msg.get("style")))
        message_rows.append(
            {
                "ObjectMessageID": message_id,
                "ObjectID": oid,
                "ObjectMessageName": msg.get("name", msg_key),
                HTML_DB_COLUMN: html,
                "ObjectMessageStyleID": style,
                "ObjectMessageOrder": msg.get("order", 10),
                "IsActive": 1 if msg.get("isActive", True) else 0,
            }
        )
        result.edges.append(
            {
                "TableName": "Object",
                "TableRowID": oid,
                "ChildTableName": "ObjectMessage",
                "ChildTableRowID": message_id,
            }
        )
        for cond in msg.get("conditions") or []:
            field_code = str(cond["field"])
            type_slug = str(cond["type"])
            cond_id = registry.require(
                "objectMessageConditions",
                object_message_condition_registry_key(msg_key, field_code, type_slug),
            )
            condition_rows.append(
                {
                    "ObjectMessageConditionID": cond_id,
                    "ObjectMessageID": message_id,
                    "ObjectLineID": registry.require("fields", field_code),
                    "ObjectMessageConditionTypeID": condition_type_id(type_slug),
                    "ObjectMessageConditionParam1": cond.get("param1"),
                    "ObjectMessageConditionParam2": cond.get("param2"),
                    "IsActive": 1,
                }
            )
            result.edges.append(
                {
                    "TableName": "ObjectMessage",
                    "TableRowID": message_id,
                    "ChildTableName": "ObjectMessageCondition",
                    "ChildTableRowID": cond_id,
                }
            )

    if message_rows:
        result.rows["ObjectMessage"] = message_rows
    if condition_rows:
        result.rows["ObjectMessageCondition"] = condition_rows


def _build_update_actions(spec: dict, registry: IdRegistry, oid: int, result: BuildResult) -> None:
    actions = spec.get("updateActions") or []
    if not actions:
        return

    action_rows: list[dict] = []
    access_rows: list[dict] = []
    condition_rows: list[dict] = []
    message_rows: list[dict] = []

    for action in actions:
        action_key = action.get("key") or slugify(str(action.get("name", "update")))
        action_id = registry.require("updateActions", action_key)

        template_key = action.get("template")
        template_id = None
        if template_key is not None:
            template_id = registry.optional("templates", str(template_key))
            if template_id is None:
                template_id = registry._scalar("objectDefaultId")  # noqa: SLF001

        workflow_key = action.get("workflow")
        workflow_id = None
        if workflow_key is not None:
            workflow_id = registry._scalar("workflowId")  # noqa: SLF001
            if workflow_id is None:
                workflow_id = registry.optional("workflows", str(workflow_key))

        row: dict[str, Any] = {
            "ObjectID": oid,
            "ObjectUpdateActionID": action_id,
            "ObjectUpdateActionName": action.get("name", action_key),
            "ObjectUpdateActionOrder": action.get("order", 10),
            "ObjectUpdateActionIsQuick": 1 if action.get("isQuick") else 0,
            "IsActive": 1 if action.get("isActive", True) else 0,
        }
        if template_id is not None:
            row["ObjectDefaultID"] = template_id
        if workflow_id is not None:
            row["WorkflowID"] = workflow_id
        reopen_id = reopen_on_save_id(action.get("reopenOnSave"))
        if reopen_id is not None:
            row["ObjectUpdateActionReopenTypeID"] = reopen_id

        tab_focus = action.get("tabFocus") or {}
        left_id = _tab_id_for_name(spec, registry, tab_focus.get("left"), placement=0)
        right_id = _tab_id_for_name(spec, registry, tab_focus.get("right"), placement=1)
        if left_id is not None:
            row["ObjectLineTabFocusLeftID"] = left_id
        if right_id is not None:
            row["ObjectLineTabFocusRightID"] = right_id

        action_rows.append(row)
        result.edges.append(
            {
                "TableName": "Object",
                "TableRowID": oid,
                "ChildTableName": "ObjectUpdateAction",
                "ChildTableRowID": action_id,
            }
        )

        for access in action.get("access") or []:
            field_code = str(access["field"])
            subline_id = access.get("sublineId")
            reg_key = access_registry_key(action_key, field_code, subline_id)
            access_id = registry.require("objectUpdateAccess", reg_key)
            line_id = registry.require("fields", field_code)
            editable_bit, visible_bit = resolve_access_flags(access)
            access_row: dict[str, Any] = {
                "ObjectUpdateActionID": action_id,
                "ObjectUpdateAccessID": access_id,
                "ObjectLineID": line_id,
                "ObjectLineIsEditableUpdate": editable_bit,
                "ObjectLineIsVisibleUpdate": visible_bit,
                "IsActive": 1,
            }
            if subline_id is not None:
                access_row["ObjectSubLineID"] = int(subline_id)
            access_rows.append(access_row)
            result.edges.append(
                {
                    "TableName": "ObjectUpdateAction",
                    "TableRowID": action_id,
                    "ChildTableName": "ObjectUpdateAccess",
                    "ChildTableRowID": access_id,
                }
            )

        for cond in action.get("conditions") or []:
            field_code = str(cond["field"])
            type_slug = str(cond["type"])
            reg_key = f"{action_key}/{field_code}/{type_slug}"
            cond_id = registry.require("objectUpdateActionConditions", reg_key)
            condition_rows.append(
                {
                    "ObjectUpdateActionID": action_id,
                    "ObjectUpdateActionConditionID": cond_id,
                    "ObjectLineID": registry.require("fields", field_code),
                    "ObjectUpdateActionConditionTypeID": condition_type_id(type_slug),
                    "ObjectUpdateActionConditionParam1": cond.get("param1"),
                    "ObjectUpdateActionConditionParam2": cond.get("param2"),
                    "IsActive": 1,
                }
            )
            result.edges.append(
                {
                    "TableName": "ObjectUpdateAction",
                    "TableRowID": action_id,
                    "ChildTableName": "ObjectUpdateActionCondition",
                    "ChildTableRowID": cond_id,
                }
            )

        for msg in action.get("messages") or []:
            msg_key = str(msg["key"])
            reg_key = f"{action_key}/{msg_key}"
            msg_link_id = registry.require("objectUpdateMessages", reg_key)
            object_message_id = registry.require("objectMessages", msg_key)
            message_rows.append(
                {
                    "ObjectUpdateMessageID": msg_link_id,
                    "ObjectUpdateActionID": action_id,
                    "ObjectMessageID": object_message_id,
                    "ObjectUpdateMessageIsVisible": 1 if msg.get("visible") else 0,
                    "IsActive": 1,
                }
            )
            result.edges.append(
                {
                    "TableName": "ObjectUpdateAction",
                    "TableRowID": action_id,
                    "ChildTableName": "ObjectUpdateMessage",
                    "ChildTableRowID": msg_link_id,
                }
            )

    if action_rows:
        result.rows["ObjectUpdateAction"] = action_rows
    if access_rows:
        result.rows["ObjectUpdateAccess"] = access_rows
    if condition_rows:
        result.rows["ObjectUpdateActionCondition"] = condition_rows
    if message_rows:
        result.rows["ObjectUpdateMessage"] = message_rows


def _build_templates(
    spec: dict,
    registry: IdRegistry,
    oid: int,
    wf_id: int,
    result: BuildResult,
) -> None:
    templates = iter_templates(spec)
    legacy = is_legacy_single_template(spec)
    fields = iter_layout_fields(spec)
    default_seen = False
    template_rows: list[dict] = []
    template_line_rows: list[dict] = []
    template_access_rows: list[dict] = []

    for index, template_cfg in enumerate(templates):
        template_key = str(template_cfg.get("key") or slugify(str(template_cfg.get("name", "default"))))
        is_default = bool(template_cfg.get("isDefault")) or (not default_seen and index == 0)
        if is_default:
            default_seen = True
        template_id = resolve_template_id(registry, template_key, is_default=is_default)
        template_rows.append(
            _object_default_row(
                spec,
                template_id=template_id,
                object_id=oid,
                workflow_id=wf_id,
                template_cfg=template_cfg,
                template_key=template_key,
                is_default=is_default,
            )
        )
        result.edges.append(
            {
                "TableName": "Object",
                "TableRowID": oid,
                "ChildTableName": "ObjectDefault",
                "ChildTableRowID": template_id,
            }
        )

        template_fields = template_cfg.get("fields") or {}
        for field in fields:
            code = str(field.get("code") or "")
            if not code:
                continue
            meta = result.field_meta.get(code) or {}
            line_id = meta.get("lineId") or registry.require("fields", code)
            template_line_id = require_template_line_id(
                registry, template_key, code, legacy=legacy
            )
            template_line: dict[str, Any] = {
                "ObjectDefaultID": template_id,
                "ObjectDefaultLineID": template_line_id,
                "ObjectLineID": line_id,
                "IsActive": 1,
            }
            field_cfg = template_fields.get(code)
            apply_template_line_validation(
                template_line,
                field=field,
                template_field=field_cfg if isinstance(field_cfg, dict) else None,
                spec=spec,
                registry=registry,
            )
            apply_template_line_extras(
                template_line,
                field=field,
                template_field=field_cfg if isinstance(field_cfg, dict) else None,
                spec=spec,
                registry=registry,
            )
            lookup_id = meta.get("lookupId")
            if lookup_id:
                template_line["ObjectDefaultLineLookupID"] = lookup_id
                source_field_id = meta.get("lookupSourceFieldId")
                if source_field_id:
                    template_line["ObjectDefaultLineLookupObjectLineID"] = source_field_id
                filter_field_id = meta.get("lookupFilterFieldId")
                if filter_field_id:
                    template_line["ObjectDefaultLineLookupFilterObjectLineID"] = filter_field_id
            autonumber_key = None
            if isinstance(field_cfg, dict):
                autonumber_key = field_cfg.get("autonumber")
            if not autonumber_key:
                autonumber_key = field.get("autonumber")
            autonumber_id = None
            if autonumber_key:
                if field.get("type") != "text":
                    raise ValueError(f"Field {code!r} autonumber requires type text")
                autonumber_id = registry.require("autonumbers", str(autonumber_key))
                template_line["ObjectDefaultLineAutoNumberID"] = autonumber_id
            template_line_rows.append(template_line)
            result.edges.append(
                {
                    "TableName": "ObjectDefault",
                    "TableRowID": template_id,
                    "ChildTableName": "ObjectDefaultLine",
                    "ChildTableRowID": template_line_id,
                }
            )
            if lookup_id:
                result.edges.append(
                    {
                        "TableName": "ObjectDefaultLine",
                        "TableRowID": template_line_id,
                        "ChildTableName": "ObjectLineLookup",
                        "ChildTableRowID": lookup_id,
                    }
                )
            if autonumber_id:
                result.edges.append(
                    {
                        "TableName": "ObjectDefaultLine",
                        "TableRowID": template_line_id,
                        "ChildTableName": "ObjectLineAutoNumber",
                        "ChildTableRowID": autonumber_id,
                    }
                )

        for access in template_cfg.get("access") or []:
            field_code = str(access["field"])
            subline_id = access.get("sublineId")
            reg_key = template_access_registry_key(
                template_key, field_code, subline_id, legacy=legacy
            )
            access_id = registry.require("objectDefaultAccess", reg_key)
            editable_bit, visible_bit = resolve_access_flags(access)
            access_row: dict[str, Any] = {
                "ObjectDefaultID": template_id,
                "ObjectDefaultAccessID": access_id,
                "ObjectLineID": registry.require("fields", field_code),
                "ObjectLineIsEditableCreate": editable_bit,
                "ObjectLineIsVisibleCreate": visible_bit,
                "IsActive": 1,
            }
            if subline_id is not None:
                access_row["ObjectSubLineID"] = int(subline_id)
            template_access_rows.append(access_row)
            result.edges.append(
                {
                    "TableName": "ObjectDefault",
                    "TableRowID": template_id,
                    "ChildTableName": "ObjectDefaultAccess",
                    "ChildTableRowID": access_id,
                }
            )

    result.rows["ObjectDefault"] = template_rows
    if template_access_rows:
        result.rows["ObjectDefaultAccess"] = template_access_rows
    result.rows["ObjectDefaultLine"] = template_line_rows


def _build_object_actions(spec: dict, registry: IdRegistry, oid: int, result: BuildResult) -> None:
    actions = spec.get("objectActions") or []
    if not actions:
        return

    action_rows: list[dict] = []
    param_rows: list[dict] = []
    condition_rows: list[dict] = []
    step_link_rows: list[dict] = []

    for action in actions:
        action_key = action.get("key") or slugify(str(action.get("name", "object_action")))
        action_id = registry.require("objectActions", action_key)
        action_rows.append(
            {
                "ObjectID": oid,
                "ObjectActionID": action_id,
                "ObjectActionName": action.get("name", action_key),
                "ObjectActionTypeCode": action["typeCode"],
                "ObjectActionOrder": action.get("order", 10),
                "IsActive": 1 if action.get("isActive", True) else 0,
            }
        )
        result.edges.append(
            {
                "TableName": "Object",
                "TableRowID": oid,
                "ChildTableName": "ObjectAction",
                "ChildTableRowID": action_id,
            }
        )

        for param_code, raw_value in iter_params(action):
            param_id = registry.require("objectActionParams", param_registry_key(action_key, param_code))
            param_rows.append(
                {
                    "ObjectActionID": action_id,
                    "ObjectActionParamID": param_id,
                    "ObjectActionTypeParamCode": param_code,
                    "ObjectActionParamValue": resolve_param_value(
                        raw_value, param_code=param_code, registry=registry
                    ),
                    "IsActive": 1,
                }
            )
            result.edges.append(
                {
                    "TableName": "ObjectAction",
                    "TableRowID": action_id,
                    "ChildTableName": "ObjectActionParam",
                    "ChildTableRowID": param_id,
                }
            )

        for cond in action.get("conditions") or []:
            field_code = str(cond["field"])
            type_slug = str(cond["type"])
            cond_id = registry.require(
                "objectActionConditions",
                condition_registry_key(action_key, field_code, type_slug),
            )
            condition_rows.append(
                {
                    "ObjectActionID": action_id,
                    "ObjectActionConditionID": cond_id,
                    "ObjectLineID": registry.require("fields", field_code),
                    "ObjectActionConditionTypeID": condition_type_id(type_slug),
                    "ObjectActionConditionParam1": cond.get("param1"),
                    "ObjectActionConditionParam2": cond.get("param2"),
                    "IsActive": 1 if cond.get("isActive", True) else 0,
                }
            )
            result.edges.append(
                {
                    "TableName": "ObjectAction",
                    "TableRowID": action_id,
                    "ChildTableName": "ObjectActionCondition",
                    "ChildTableRowID": cond_id,
                }
            )

        for step_name in action.get("workflowSteps") or []:
            step_id = registry.require("workflowSteps", str(step_name))
            link_id = registry.require(
                "workflowStepObjectActions",
                step_link_registry_key(action_key, str(step_name)),
            )
            step_link_rows.append(
                {
                    "WorkflowStepObjectActionID": link_id,
                    "WorkflowStepID": step_id,
                    "ObjectActionID": action_id,
                    "IsActive": 1,
                }
            )
            result.edges.append(
                {
                    "TableName": "WorkflowStep",
                    "TableRowID": step_id,
                    "ChildTableName": "WorkflowStepObjectAction",
                    "ChildTableRowID": link_id,
                }
            )

    if action_rows:
        result.rows["ObjectAction"] = action_rows
    if param_rows:
        result.rows["ObjectActionParam"] = param_rows
    if condition_rows:
        result.rows["ObjectActionCondition"] = condition_rows
    if step_link_rows:
        result.rows["WorkflowStepObjectAction"] = step_link_rows


def build_rows(spec: dict) -> BuildResult:
    spec = normalize_spec(spec)
    validate_spec(spec)
    mapping = load_field_mapping()
    registry = build_registry(spec)
    obj = spec["object"]
    result = BuildResult()

    company_id = registry.require_scalar("companyId")
    ot_id = registry.require_scalar("objectTypeId")
    oid = registry.require_scalar("objectId")

    company = spec.get("company") or {}
    company_name = company.get("name") or f"{obj['name']} Company"
    company_row: dict[str, Any] = {
        "CompanyID": company_id,
        "CompanyName": company_name,
        "CompanyOrder": 0,
        "IsActive": 1,
    }
    _set_optional_nonempty(company_row, "CompanyTreeIcon", company.get("icon"))
    result.rows["Company"] = [company_row]

    object_type = spec.get("objectType") or {}
    object_type_row: dict[str, Any] = {
        "ObjectTypeID": ot_id,
        "ObjectTypeName": obj.get("objectType", "General"),
        "ObjectTypeOrder": 0,
        "IsActive": 1,
    }
    _set_optional_nonempty(object_type_row, "ObjectTypeTreeIcon", object_type.get("icon"))
    _set_optional_nonempty(object_type_row, "ObjectTypeTreeColorBack", object_type.get("color"))
    result.rows["ObjectType"] = [object_type_row]

    object_row: dict[str, Any] = {
        "ObjectID": oid,
        "ObjectTypeID": ot_id,
        "CompanyID": company_id,
        "ObjectName": obj["name"],
        "ObjectCode": obj.get("code"),
        "IsActive": 1,
    }
    _set_optional_nonempty(object_row, "ObjectTreeIcon", obj.get("icon"))
    _set_optional_nonempty(object_row, "ObjectTreeColor", obj.get("color"))
    result.rows["Object"] = [object_row]
    result.edges.extend(
        [
            {"TableName": "Object", "TableRowID": oid, "ChildTableName": "Object", "ChildTableRowID": oid},
            {
                "TableName": "Object",
                "TableRowID": oid,
                "ChildTableName": "Company",
                "ChildTableRowID": company_id,
            },
            {
                "TableName": "Object",
                "TableRowID": oid,
                "ChildTableName": "ObjectType",
                "ChildTableRowID": ot_id,
            },
        ]
    )

    _emit_sources(spec, registry, result)
    _emit_lookups(spec, registry, result)
    _emit_autonumbers(spec, registry, result)

    tab_rows = []
    section_rows = []
    line_rows = []
    line_index = 0

    for tab in spec["layout"]["tabs"]:
        tab_name = tab["name"]
        tab_id = registry.require("tabs", tab_name)
        tab_row: dict[str, Any] = {
            "ObjectLineTabID": tab_id,
            "ObjectLineTabName": tab_name,
            "ObjectLineTabOrder": tab.get("order", 1),
            "ObjectLineTabPlacement": tab.get("placement", 0),
            "IsActive": 1,
        }
        _set_optional_bool(tab_row, "ObjectLineTabAlwaysHidden", tab.get("alwaysHidden"))
        tab_rows.append(tab_row)
        for section in tab.get("sections", []):
            section_name = section["name"]
            sec_key = _section_key(tab_name, section_name)
            section_id = registry.require("sections", sec_key)
            section_rows.append(
                {
                    "ObjectLineSectionID": section_id,
                    "ObjectSectionName": section_name,
                    "ObjectSectionOrder": section.get("order", 1),
                    "ObjectSectionWidth": section.get("width", 100),
                    "ObjectLineTabID": tab_id,
                    "IsActive": 1,
                }
            )
            result.edges.append(
                {
                    "TableName": "ObjectLineTab",
                    "TableRowID": tab_id,
                    "ChildTableName": "ObjectLineSection",
                    "ChildTableRowID": section_id,
                }
            )
            for field in section.get("fields", []):
                line_index += 1
                ftype = field["type"]
                type_info = mapping[ftype]
                code = field.get("code", f"FIELD_{line_index}")
                line_id = registry.require("fields", str(code))

                line_row = {
                    "ObjectID": oid,
                    "ObjectLineID": line_id,
                    "ObjectLineSectionID": section_id,
                    "ObjectLineSlot": field.get("slot", line_index),
                    "ObjectLineName": field["name"],
                    "ObjectLineOrder": field.get("order", line_index * 10),
                    "ObjectLineTypeID": type_info["objectLineTypeId"],
                    "ObjectLineTypeWidth": field.get("width", 100),
                    "IsActive": 1 if field.get("isActive", True) else 0,
                }
                if field.get("code"):
                    line_row["ObjectLineCode"] = field["code"]
                _set_optional_bool(line_row, "ObjectLineIsHidden", field.get("alwaysHidden"))
                if ftype == "number" and field.get("precision") is not None:
                    line_row["ObjectLineNumberPrecision"] = field["precision"]
                if ftype == "subgrid" and field.get("objectSubId") is not None:
                    line_row["ObjectSubID"] = field["objectSubId"]
                if ftype == "button" and field.get("saveAction") is not None:
                    line_row["ObjectLineButtonSaveAction"] = field["saveAction"]
                _apply_object_line_extras(line_row, field, ftype, registry)

                ongrid_field = (spec.get("onGrid") or {}).get("fields", {}).get(code, {})
                if "allowed" in ongrid_field:
                    line_row["ObjectLineOnGridIsAllowed"] = 1 if ongrid_field.get("allowed") else 0
                elif ongrid_field:
                    line_row["ObjectLineOnGridIsAllowed"] = 1
                if ongrid_field.get("name"):
                    line_row["ObjectLineOnGridName"] = ongrid_field["name"]
                if "isTag" in ongrid_field:
                    line_row["ObjectLineOnGridIsTag"] = 1 if ongrid_field["isTag"] else 0
                if ongrid_field.get("isSearch"):
                    line_row["ObjectLineOnGridIsSearch"] = 1
                if ongrid_field.get("isTotal"):
                    line_row["ObjectLineOnGridIsTotal"] = 1

                line_rows.append(line_row)
                result.edges.extend(
                    [
                        {
                            "TableName": "Object",
                            "TableRowID": oid,
                            "ChildTableName": "ObjectLine",
                            "ChildTableRowID": line_id,
                        },
                        {
                            "TableName": "ObjectLine",
                            "TableRowID": line_id,
                            "ChildTableName": "ObjectLineTab",
                            "ChildTableRowID": tab_id,
                        },
                    ]
                )
                result.field_meta[code] = {
                    "lineId": line_id,
                    "tabId": tab_id,
                    "sectionId": section_id,
                }

                reference = field.get("reference")
                lookup = field.get("lookup")

                if reference and ftype in REFERENCE_FIELD_TYPES:
                    source_id = _resolve_source_id(spec, registry, reference)
                    line_row["ObjectLineSourceID"] = source_id
                    filter_field = reference.get("filterField")
                    if filter_field:
                        line_row["ObjectLineSourceFilterObjectLineID"] = registry.require(
                            "fields", str(filter_field)
                        )
                    result.edges.append(
                        {
                            "TableName": "ObjectLine",
                            "TableRowID": line_id,
                            "ChildTableName": "ObjectLineSource",
                            "ChildTableRowID": source_id,
                        }
                    )
                    result.field_meta[code]["sourceId"] = source_id

                if lookup and ftype in LOOKUP_FIELD_TYPES:
                    source_field = lookup.get("sourceField")
                    if not source_field:
                        raise ValueError(f"Field {code!r} lookup requires sourceField")
                    lookup_key = _field_lookup_key(field, lookup)
                    lookup_id = registry.require("lookups", lookup_key)
                    result.field_meta[code]["lookupId"] = lookup_id
                    result.field_meta[code]["lookupSourceFieldId"] = registry.require(
                        "fields", str(source_field)
                    )
                    filter_field = lookup.get("filterField")
                    if filter_field:
                        result.field_meta[code]["lookupFilterFieldId"] = registry.require(
                            "fields", str(filter_field)
                        )

    result.rows["ObjectLineTab"] = tab_rows
    result.rows["ObjectLineSection"] = section_rows
    result.rows["ObjectLine"] = line_rows

    title_field = obj.get("requestTitleField")
    if title_field:
        object_row["RequestTitleObjectLineID"] = registry.require("fields", str(title_field))

    grid_sort = obj.get("gridSort") or {}
    sort_field = grid_sort.get("field")
    if sort_field:
        sort_type = str(grid_sort.get("type") or "").upper()
        if sort_type not in ("ASC", "DESC"):
            raise ValueError(
                f"object.gridSort.type must be ASC or DESC, got {grid_sort.get('type')!r}"
            )
        object_row["ObjectGridSortObjectLineID"] = registry.require("fields", str(sort_field))
        object_row["ObjectGridSortType"] = sort_type

    wf_cfg = spec.get("workflow", {})
    if wf_cfg.get("mode") == "full" and wf_cfg.get("steps"):
        wf_id = _build_workflow_full(spec, registry, oid, result)
    elif _workflow_reused(spec):
        wf_id = registry.require_scalar("workflowId")
        _emit_workflow_step_access(spec, registry, result, wf_cfg.get("steps") or [])
    else:
        wf_id = _build_workflow_minimal(spec, registry, oid, result)

    if not _workflow_reused(spec):
        _emit_roles_and_statuses(spec, registry, result)

    _build_templates(spec, registry, oid, wf_id, result)

    ongrid_rows = []
    used_legacy_ongrid: set[str] = set()
    for layout in (spec.get("onGrid") or {}).get("layouts", []):
        size = layout.get("size", "Large")
        grid_type = layout.get("type", "Grid")
        module = layout.get("module", "Items")
        for placement in layout.get("placements", []):
            row_letter = placement.get("row", "T")
            for col in placement.get("columns", []):
                code = col["field"]
                meta = result.field_meta.get(code)
                if not meta:
                    continue
                og_id = require_ongrid_id(
                    registry,
                    size=size,
                    grid_type=grid_type,
                    module=module,
                    field_code=code,
                    used_legacy=used_legacy_ongrid,
                )
                ongrid_rows.append(
                    {
                        "ObjectLineOnGridID": og_id,
                        "ObjectID": oid,
                        "ObjectLineID": meta["lineId"],
                        "ObjectLineOnGridSize": size,
                        "ObjectLineOnGridType": grid_type,
                        "ObjectLineOnGridModule": module,
                        "ObjectLineOnGridRow": row_letter,
                        "ObjectLineOnGridPosition": col.get("position", 1),
                        "ObjectLineOnGridLength": col.get("length", 100),
                        "ObjectLineOnGridValueWidth": col.get("valueWidth", 0),
                        "ObjectLineOnGridLabelType": col.get("labelType", 1),
                        "IsActive": 1,
                    }
                )
                result.edges.append(
                    {
                        "TableName": "Object",
                        "TableRowID": oid,
                        "ChildTableName": "ObjectLineOnGrid",
                        "ChildTableRowID": og_id,
                    }
                )
    if ongrid_rows:
        result.rows["ObjectLineOnGrid"] = ongrid_rows

    _build_object_messages(spec, registry, oid, result)
    _build_update_actions(spec, registry, oid, result)
    _build_object_actions(spec, registry, oid, result)
    emit_language_table(spec, registry, result)

    return result
