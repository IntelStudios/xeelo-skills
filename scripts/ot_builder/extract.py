"""Build xeelo-spec from parsed Object transfer."""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

from ot_builder.comments import extract_comments
from ot_builder.language_table import extract_language_table
from ot_builder.ongrid import layout_id_key
from ot_builder.system_line import code_for_id, explicit_key_token
from ot_builder.reopen import reopen_on_save_spec
from ot_builder.parse import TransferIndex, collect_table_max_ids, find_object_row, load_transfer
from ot_builder.object_actions import (
    condition_registry_key,
    param_registry_key,
    param_spec_value,
    step_link_registry_key,
)
from ot_builder.object_messages import (
    condition_registry_key as object_message_condition_registry_key,
    html_from_row,
    message_key,
    style_slug,
)
from ot_builder.periodics import extract_periodics
from ot_builder.notifications import (
    WORKFLOW_NOTIFICATION_FIELDS,
    extract_notifications,
    step_notification_registry_key,
    _nid,
)
from ot_builder.templates import (
    COMBO_FIELD_TYPES,
    LOOKUP_FIELD_TYPES,
    REFERENCE_FIELD_TYPES,
    template_access_registry_key,
    template_field_spec_from_line,
    template_line_key,
    template_slug_from_name,
)
from ot_builder.update_actions import (
    access_differs_from_default,
    access_registry_key,
    condition_slug,
    slugify,
    step_access_differs_from_default,
    step_access_registry_key,
    template_access_differs_from_default,
)

DATA = Path(__file__).resolve().parent.parent.parent / "data"

MINIMAL_STEP_NAMES = ("Draft", "Active")
MINIMAL_ACTION_NAMES = ("Submit", "Complete")


@lru_cache(maxsize=1)
def _load_field_mapping() -> dict:
    return json.loads((DATA / "field-type-mapping.json").read_text(encoding="utf-8"))


def _type_id_to_spec(mapping: dict) -> dict[int, str]:
    return {info["objectLineTypeId"]: name for name, info in mapping.items()}


def _int(val: Any) -> int | None:
    if val is None:
        return None
    return int(val)


def _boolish(val: Any) -> bool:
    return str(val) in ("1", "True", "true")


def _nonempty_str(row: dict[str, Any] | None, column: str) -> str | None:
    if not row:
        return None
    val = row.get(column)
    if val is None:
        return None
    text = str(val).strip()
    return text or None


def _object_line_code(index: TransferIndex, line_id: int | None) -> str | None:
    if line_id is None:
        return None
    row = index.row_by_id("ObjectLine", line_id)
    if not row:
        return None
    return row.get("ObjectLineCode") or f"LINE_{line_id}"


def _emit_true(field: dict[str, Any], key: str, value: Any) -> None:
    if _boolish(value):
        field[key] = True


def _apply_extracted_line_extras(
    field: dict[str, Any],
    line: dict[str, Any],
    ftype: str,
    index: TransferIndex,
) -> None:
    unique_id = _int(line.get("ObjectLineUniqueID"))
    if unique_id:
        field["uniqueId"] = unique_id

    if ftype == "number":
        if line.get("ObjectLineNumberSeparator"):
            field["numberSeparator"] = line["ObjectLineNumberSeparator"]
        number_min = _int(line.get("ObjectLineNumberMin"))
        if number_min is not None:
            field["numberMin"] = number_min
        number_max = _int(line.get("ObjectLineNumberMax"))
        if number_max is not None:
            field["numberMax"] = number_max
    if ftype == "text":
        text_input = _int(line.get("ObjectLineTextInputType"))
        if text_input:
            field["textInputType"] = text_input
    if ftype in ("radio", "checkbox_multiselect"):
        columns = _int(line.get("ObjectLineNumberColumns"))
        if columns is not None and columns != 1:
            field["columnNumbers"] = columns
    if ftype == "web_frame":
        web_frame = _int(line.get("WebFrameTypeID"))
        if web_frame:
            field["webFrameTypeId"] = web_frame
    if ftype in ("memo", "report"):
        height = _int(line.get("ObjectLineHeight"))
        if height:
            field["height"] = height
    if ftype == "description_memo":
        _emit_true(field, "descMemoBorder", line.get("ObjectLineDescMemoIsBorder"))
        padding = _int(line.get("ObjectLineDescMemoPadding"))
        if padding is not None:
            field["descMemoPadding"] = padding
    if ftype == "button":
        if line.get("ObjectLineButtonMessage"):
            field["buttonMessage"] = line["ObjectLineButtonMessage"]
        if line.get("ObjectLineColorFont"):
            field["colorFont"] = line["ObjectLineColorFont"]
        if line.get("ObjectLineColorBack"):
            field["colorBack"] = line["ObjectLineColorBack"]
    if ftype in COMBO_FIELD_TYPES:
        _emit_true(field, "isReferenceLink", line.get("ObjectLineIsReferenceLink"))
    if ftype == "attachment":
        storage_id = _int(line.get("AttachmentStorageID"))
        if storage_id:
            field["attachmentStorageId"] = storage_id
        _emit_true(field, "ocr", line.get("ObjectLineAttachmentIsOCR"))
        if line.get("ObjectLineAttachmentOCRLang"):
            field["ocrLang"] = line["ObjectLineAttachmentOCRLang"]
        resize = _int(line.get("ObjectLineAttachmentImageResizeMax"))
        if resize:
            field["imageResizeMax"] = resize
        _emit_true(field, "mobileScan", line.get("ObjectLineAttachmentMobileIsScan"))
        _emit_true(field, "mobileSignature", line.get("ObjectLineAttachmentMobileIsSignature"))
    if ftype == "attachment_preview":
        preview_code = _object_line_code(index, _int(line.get("ObjectLineAttPreviewObjectLineID")))
        if preview_code:
            field["previewField"] = preview_code
        if line.get("ObjectLineAttPreviewIsDownload") is not None and not _boolish(
            line.get("ObjectLineAttPreviewIsDownload")
        ):
            field["previewDownload"] = False


def _slug(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", name.strip().lower()).strip("_")
    return slug or "item"


def _disambiguate_key(used: set[str], name: str, row_id: int, *, colliding: bool) -> str:
    """Keep unique display names as keys; suffix ``_{row_id}`` when names collide."""
    if not colliding:
        used.add(name)
        return name
    base = _slug(name)
    key = f"{base}_{row_id}"
    suffix = row_id
    while key in used:
        suffix += 1
        key = f"{base}_{suffix}"
    used.add(key)
    return key


def _assign_keys(
    items: dict[int, dict[str, Any]],
    *,
    merge_keys: dict[int, str] | None = None,
) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    merge_keys = merge_keys or {}
    id_to_key: dict[int, str] = dict(merge_keys)
    used: set[str] = set(id_to_key.values())
    specs: dict[str, dict[str, Any]] = {}

    for row_id in sorted(items.keys()):
        if row_id in id_to_key:
            key = id_to_key[row_id]
        else:
            base = _slug(items[row_id]["name"])
            key = base
            suffix = row_id
            while key in used:
                key = f"{base}_{suffix}"
                suffix += 1
            id_to_key[row_id] = key
            used.add(key)
        specs[key] = items[row_id]["spec"]

    explicit = {key: row_id for row_id, key in id_to_key.items()}
    return specs, explicit


def _role_spec(row: dict) -> dict[str, Any]:
    spec: dict[str, Any] = {
        "name": row.get("RoleName", ""),
        "isRequestor": _boolish(row.get("IsRequestor")),
        "isOwner": _boolish(row.get("IsOwner")),
    }
    if not _boolish(row.get("IsActive", 1)):
        spec["isActive"] = False
    return spec


def _status_spec(row: dict) -> dict[str, Any]:
    spec: dict[str, Any] = {
        "name": row.get("RequestStatusName", ""),
        "order": int(row.get("RequestStatusOrder", 10)),
        "isCompleted": _boolish(row.get("RequestStatusIsCompleted")),
        "isCanceled": _boolish(row.get("RequestStatusIsCanceled")),
    }
    if not _boolish(row.get("IsActive", 1)):
        spec["isActive"] = False
    return spec


def _collect_role_status_ids(
    wf_row: dict,
    steps: list[dict],
    actions_by_step: dict[int, list[dict]],
) -> tuple[set[int], set[int]]:
    role_ids: set[int] = set()
    status_ids: set[int] = set()

    def track(role_id: Any, status_id: Any) -> None:
        if role_id is not None:
            role_ids.add(int(role_id))
        if status_id is not None:
            status_ids.add(int(status_id))

    track(wf_row.get("RoleID"), wf_row.get("RequestStatusID"))
    for step in steps:
        track(step.get("RoleID"), step.get("RequestStatusID"))
        for action in actions_by_step.get(int(step["WorkflowStepID"]), []):
            track(action.get("RoleID"), action.get("RequestStatusID"))
    return role_ids, status_ids


def _build_roles_statuses(
    index: TransferIndex,
    role_ids: set[int],
    status_ids: set[int],
    merge: dict | None,
) -> tuple[dict[str, dict], dict[str, dict], dict[str, int], dict[str, int]]:
    merge_roles = ((merge or {}).get("roles") or {}) if merge else {}
    merge_statuses = ((merge or {}).get("statuses") or {}) if merge else {}
    merge_role_ids = {
        int(v): k for k, v in ((merge or {}).get("ids", {}).get("explicit", {}).get("roles") or {}).items()
    }
    merge_status_ids = {
        int(v): k for k, v in ((merge or {}).get("ids", {}).get("explicit", {}).get("statuses") or {}).items()
    }

    role_items: dict[int, dict[str, Any]] = {}
    for role_id in role_ids:
        row = index.row_by_id("Role", role_id)
        if not row:
            continue
        spec = _role_spec(row)
        if role_id in merge_role_ids and merge_roles.get(merge_role_ids[role_id]):
            spec = {**spec, **{k: v for k, v in merge_roles[merge_role_ids[role_id]].items() if k != "name" or v}}
        role_items[role_id] = {"name": row.get("RoleName", ""), "spec": spec}

    status_items: dict[int, dict[str, Any]] = {}
    for status_id in status_ids:
        row = index.row_by_id("RequestStatus", status_id)
        if not row:
            continue
        spec = _status_spec(row)
        if status_id in merge_status_ids and merge_statuses.get(merge_status_ids[status_id]):
            spec = {
                **spec,
                **{k: v for k, v in merge_statuses[merge_status_ids[status_id]].items() if k != "name" or v},
            }
        status_items[status_id] = {"name": row.get("RequestStatusName", ""), "spec": spec}

    roles, explicit_roles = _assign_keys(role_items, merge_keys=merge_role_ids)
    statuses, explicit_statuses = _assign_keys(status_items, merge_keys=merge_status_ids)
    return roles, statuses, explicit_roles, explicit_statuses


REQUEST_TYPE_NAMES = {0: "all", 1: "completed", 2: "in-progress"}

REF_OBJECT_LINE_ROLES = {
    "ValueObjectLineID": "value",
    "ValueNameObjectLineID": "valueName",
    "ValueBindObjectLineID": "valueBind",
    "ValueFilterObjectLineID": "valueFilter",
    "ValueOrderObjectLineID": "valueOrder",
}


def _line_code_for_object(index: TransferIndex, object_id: int, line_id: int | None) -> str | None:
    if line_id is None:
        return None
    row = index.row_by_id("ObjectLine", int(line_id))
    if row and int(row.get("ObjectID", 0)) == int(object_id):
        return row.get("ObjectLineCode") or f"LINE_{line_id}"
    return f"LINE_{line_id}"


def _source_values(index: TransferIndex, source_id: int) -> list[dict]:
    values = []
    for row in index.rows_for("ObjectLineSourceValue", "ObjectLineSourceID", source_id):
        entry: dict[str, Any] = {
            "value": row.get("ObjectLineSourceValue", ""),
            "label": row.get("ObjectLineSourceValueName", ""),
        }
        bind = row.get("ObjectLineSourceValueBind")
        if bind and bind != entry["value"]:
            entry["bind"] = bind
        order = row.get("ObjectLineSourceValueOrder")
        if order is not None and int(order) != 0:
            entry["order"] = int(order)
        values.append(entry)
    values.sort(key=lambda item: item.get("order", 0))
    return values


def _source_ref_object(index: TransferIndex, source_id: int) -> dict | None:
    for row in index.rows_for("ObjectLineSourceRefObject", "ObjectLineSourceID", source_id):
        if not _boolish(row.get("IsActive", 1)):
            continue
        object_id = int(row["ObjectID"])
        ref: dict[str, Any] = {
            "objectId": object_id,
            "requestType": REQUEST_TYPE_NAMES.get(
                int(row.get("ObjectLineSourceRefObjectRequestTypeID", 0)), "all"
            ),
        }
        if row.get("ObjectLineSourceRefObjectName"):
            ref["name"] = row["ObjectLineSourceRefObjectName"]
        lines: dict[str, str] = {}
        for column, role in REF_OBJECT_LINE_ROLES.items():
            line_id = _int(row.get(column))
            if line_id is not None:
                code = _line_code_for_object(index, object_id, line_id)
                if code:
                    lines[role] = code
        if lines:
            ref["lines"] = lines
        return ref
    return None


def _build_sources(
    index: TransferIndex,
    source_ids: set[int],
) -> tuple[dict[str, dict], dict[str, int], dict[str, int], dict[str, int], dict[str, int]]:
    source_items: dict[int, dict[str, Any]] = {}
    explicit_source_values: dict[str, int] = {}
    explicit_ref_lines: dict[str, int] = {}

    for source_id in source_ids:
        row = index.row_by_id("ObjectLineSource", source_id)
        if not row:
            continue
        type_id = int(row.get("ObjectLineSourceTypeID", 1))
        if type_id >= 10:
            continue

        values = _source_values(index, source_id)
        ref_object = _source_ref_object(index, source_id)
        if not values and not ref_object:
            continue

        spec_entry: dict[str, Any] = {
            "name": row.get("ObjectLineSourceName", f"Source {source_id}"),
            "typeId": type_id,
        }
        if row.get("ObjectLineSourceStyleID") is not None:
            spec_entry["styleId"] = int(row["ObjectLineSourceStyleID"])
        if values:
            spec_entry["values"] = values
            for value_row in index.rows_for("ObjectLineSourceValue", "ObjectLineSourceID", source_id):
                explicit_source_values[str(value_row["ObjectLineSourceValue"])] = int(
                    value_row["ObjectLineSourceValueID"]
                )
        if ref_object:
            spec_entry["refObject"] = ref_object
            for ref_row in index.rows_for(
                "ObjectLineSourceRefObject", "ObjectLineSourceID", source_id
            ):
                object_id = int(ref_row["ObjectID"])
                for column in REF_OBJECT_LINE_ROLES:
                    line_id = _int(ref_row.get(column))
                    if line_id is not None:
                        code = _line_code_for_object(index, object_id, line_id)
                        if code:
                            explicit_ref_lines[code] = line_id

        source_items[source_id] = {"name": spec_entry["name"], "spec": spec_entry}

    sources, explicit_sources = _assign_keys(source_items)
    explicit_ref_objects_by_source_key: dict[str, int] = {}
    for source_id, key in ((v, k) for k, v in explicit_sources.items()):
        for ref_row in index.rows_for("ObjectLineSourceRefObject", "ObjectLineSourceID", source_id):
            explicit_ref_objects_by_source_key[key] = int(ref_row["ObjectLineSourceRefObjectID"])
            break

    return sources, explicit_sources, explicit_source_values, explicit_ref_objects_by_source_key, explicit_ref_lines


def _section_key(tab_name: str, section_name: str) -> str:
    return f"{tab_name}/{section_name}"


def _collect_subtree_ids(index: TransferIndex, object_id: int) -> dict[str, dict[str, int]]:
    nodes = index.descendants("Object", object_id)
    return index.collect_by_table(nodes)


def _default_template(index: TransferIndex, object_id: int) -> dict | None:
    defaults = list(index.rows_for("ObjectDefault", "ObjectID", object_id))
    if not defaults:
        return None
    for row in defaults:
        if _boolish(row.get("ObjectDefaultIsDefault")):
            return row
    return sorted(defaults, key=lambda r: r.get("ObjectDefaultOrder", 0))[0]


def _template_lines(index: TransferIndex, template_id: int) -> dict[int, dict]:
    return {
        int(row["ObjectLineID"]): row
        for row in index.rows_for("ObjectDefaultLine", "ObjectDefaultID", template_id)
    }


def _lookup_values(index: TransferIndex, lookup_id: int) -> list[dict]:
    values = []
    for row in index.rows_for("ObjectLineLookupValue", "ObjectLineLookupID", lookup_id):
        entry: dict[str, Any] = {
            "source": row.get("ObjectLineLookupSourceValue", ""),
            "return": row.get("ObjectLineLookupReturnValue", ""),
        }
        filt = row.get("ObjectLineLookupFilterValue")
        if filt not in (None, ""):
            entry["filter"] = filt
        source_to = row.get("ObjectLineLookupSourceValue1")
        if source_to not in (None, ""):
            entry["sourceTo"] = source_to
        values.append(entry)
    return values


def _lookup_name(index: TransferIndex, lookup_id: int) -> str:
    row = index.row_by_id("ObjectLineLookup", lookup_id)
    return row.get("ObjectLineLookupName", "") if row else ""


def _lookup_value_id_key(lookup_key: str, row: dict) -> str:
    source = row.get("ObjectLineLookupSourceValue", "")
    ret = row.get("ObjectLineLookupReturnValue", "")
    filt = row.get("ObjectLineLookupFilterValue") or ""
    return f"{lookup_key}|{source}|{filt}|{ret}"


def _build_lookups(
    index: TransferIndex,
    lookup_ids: set[int],
) -> tuple[dict[str, dict], dict[str, int], dict[str, int]]:
    items: dict[int, dict[str, Any]] = {}
    for lookup_id in lookup_ids:
        row = index.row_by_id("ObjectLineLookup", lookup_id)
        if not row:
            continue
        spec_entry: dict[str, Any] = {
            "name": row.get("ObjectLineLookupName") or _lookup_name(index, lookup_id),
            "values": _lookup_values(index, lookup_id),
        }
        match_id = _int(row.get("ObjectLineLookupMatchID"))
        if match_id and match_id != 1:
            spec_entry["matchId"] = match_id
        items[lookup_id] = {"name": spec_entry["name"], "spec": spec_entry}

    lookups, explicit_lookups = _assign_keys(items)
    explicit_lookup_values: dict[str, int] = {}
    key_by_id = {row_id: key for key, row_id in explicit_lookups.items()}
    for lookup_id, key in key_by_id.items():
        for row in index.rows_for("ObjectLineLookupValue", "ObjectLineLookupID", lookup_id):
            explicit_lookup_values[_lookup_value_id_key(key, row)] = int(
                row["ObjectLineLookupValueID"]
            )
    return lookups, explicit_lookups, explicit_lookup_values


def _build_autonumbers(
    index: TransferIndex,
    autonumber_ids: set[int],
) -> tuple[dict[str, dict], dict[str, int]]:
    items: dict[int, dict[str, Any]] = {}
    for autonumber_id in autonumber_ids:
        row = index.row_by_id("ObjectLineAutoNumber", autonumber_id)
        if not row:
            continue
        spec_entry: dict[str, Any] = {
            "description": row.get("ObjectLineAutoNumberDescription") or f"autonumber_{autonumber_id}",
            "format": row.get("ObjectLineAutoNumberFormat") or "",
            "next": int(row.get("ObjectLineAutoNumberNext") or 1),
        }
        reset_id = _int(row.get("ObjectLineAutoNumberResetTypeID"))
        if reset_id:
            spec_entry["resetTypeId"] = reset_id
        items[autonumber_id] = {"name": spec_entry["description"], "spec": spec_entry}
    return _assign_keys(items)


def _line_code_by_id(index: TransferIndex, line_id: int | None) -> str | None:
    if line_id is None:
        return None
    row = index.row_by_id("ObjectLine", line_id)
    if not row:
        return None
    return row.get("ObjectLineCode") or f"LINE_{line_id}"


def _build_layout(
    index: TransferIndex,
    object_id: int,
    template_lines: dict[int, dict],
    type_map: dict[int, str],
) -> tuple[list[dict], dict[str, Any], dict[str, dict], dict[str, dict]]:
    tabs_by_id: dict[int, dict] = {}
    sections_by_id: dict[int, dict] = {}

    for row in index.rows.get("ObjectLineTab", []):
        tabs_by_id[int(row["ObjectLineTabID"])] = row
    for row in index.rows.get("ObjectLineSection", []):
        sections_by_id[int(row["ObjectLineSectionID"])] = row

    lines = list(index.rows_for("ObjectLine", "ObjectID", object_id))
    lines.sort(key=lambda r: (r.get("ObjectLineTabID") or 0, r.get("ObjectLineOrder", 0)))

    tab_layout: dict[int, dict] = {}
    explicit_fields: dict[str, int] = {}
    explicit_sections: dict[str, int] = {}
    explicit_tabs: dict[str, int] = {}
    explicit_default_lines: dict[str, int] = {}
    used_source_ids: set[int] = set()
    used_lookup_ids: set[int] = set()

    for line in lines:
        line_id = int(line["ObjectLineID"])
        section_id = int(line["ObjectLineSectionID"])
        section = sections_by_id.get(section_id)
        if not section:
            continue
        tab_id = int(section["ObjectLineTabID"])
        tab = tabs_by_id.get(tab_id)
        if not tab:
            continue

        tab_name = tab["ObjectLineTabName"]
        section_name = section["ObjectSectionName"]
        tab_entry = tab_layout.setdefault(
            tab_id,
            {
                "name": tab_name,
                "placement": tab.get("ObjectLineTabPlacement", 0),
                "order": tab.get("ObjectLineTabOrder", 1),
                "sections": {},
            },
        )
        if _boolish(tab.get("ObjectLineTabAlwaysHidden")):
            tab_entry["alwaysHidden"] = True
        explicit_tabs[tab_name] = tab_id

        sec_key = _section_key(tab_name, section_name)
        section_entry = tab_entry["sections"].setdefault(
            section_id,
            {
                "name": section_name,
                "order": section.get("ObjectSectionOrder", 1),
                "width": section.get("ObjectSectionWidth") or 100,
                "fields": [],
            },
        )
        explicit_sections[sec_key] = section_id

        type_id = int(line.get("ObjectLineTypeID", 3))
        ftype = type_map.get(type_id, "text")
        code = line.get("ObjectLineCode") or f"LINE_{line_id}"
        explicit_fields[str(code)] = line_id

        field: dict[str, Any] = {
            "name": line["ObjectLineName"],
            "code": code,
            "type": ftype,
            "slot": line.get("ObjectLineSlot"),
            "width": line.get("ObjectLineTypeWidth", 100),
            "order": line.get("ObjectLineOrder"),
        }
        if ftype == "number" and line.get("ObjectLineNumberPrecision") is not None:
            field["precision"] = int(line["ObjectLineNumberPrecision"])
        if ftype == "subgrid" and line.get("ObjectSubID") is not None:
            field["objectSubId"] = int(line["ObjectSubID"])
        if ftype == "button" and line.get("ObjectLineButtonSaveAction") is not None:
            field["saveAction"] = int(line["ObjectLineButtonSaveAction"])
        _apply_extracted_line_extras(field, line, ftype, index)
        _emit_true(field, "alwaysHidden", line.get("ObjectLineIsHidden"))
        if not _boolish(line.get("IsActive", 1)):
            field["isActive"] = False

        source_id = _int(line.get("ObjectLineSourceID"))
        filter_line_id = _int(line.get("ObjectLineSourceFilterObjectLineID"))
        if source_id and ftype in REFERENCE_FIELD_TYPES:
            used_source_ids.add(source_id)
            field["_sourceId"] = source_id
        if filter_line_id is not None:
            code_for_filter = _line_code_by_id(index, filter_line_id)
            if code_for_filter:
                field["_filterField"] = code_for_filter

        tl = template_lines.get(line_id)
        if tl:
            explicit_default_lines[str(code)] = int(tl["ObjectDefaultLineID"])
            if _int(tl.get("ObjectDefaultLineValidationID")) == 1:
                field["mandatory"] = True
            lookup_id = _int(tl.get("ObjectDefaultLineLookupID"))
            if lookup_id and ftype in LOOKUP_FIELD_TYPES:
                used_lookup_ids.add(lookup_id)
                field["_lookupId"] = lookup_id
                source_field_code = _line_code_by_id(
                    index, _int(tl.get("ObjectDefaultLineLookupObjectLineID"))
                )
                if source_field_code:
                    field["_lookupSourceField"] = source_field_code
                filter_field_code = _line_code_by_id(
                    index, _int(tl.get("ObjectDefaultLineLookupFilterObjectLineID"))
                )
                if filter_field_code:
                    field["_lookupFilterField"] = filter_field_code

        section_entry["fields"].append(field)

    sources_spec, explicit_sources, explicit_source_values, explicit_ref_objects, explicit_ref_lines = _build_sources(
        index, used_source_ids
    )
    source_id_to_key = {source_id: key for key, source_id in explicit_sources.items()}
    lookups_spec, explicit_lookups, explicit_lookup_values = _build_lookups(index, used_lookup_ids)
    lookup_id_to_key = {lookup_id: key for key, lookup_id in explicit_lookups.items()}

    tabs: list[dict] = []
    for tab_id in sorted(tab_layout.keys(), key=lambda tid: tab_layout[tid]["order"]):
        tab_data = tab_layout[tab_id]
        sections = []
        for section_id in sorted(
            tab_data["sections"].keys(),
            key=lambda sid: tab_data["sections"][sid]["order"],
        ):
            sec = tab_data["sections"][section_id]
            for field in sec["fields"]:
                source_id = field.pop("_sourceId", None)
                filter_field = field.pop("_filterField", None)
                if source_id:
                    if source_id in source_id_to_key:
                        ref: dict[str, Any] = {"reference": source_id_to_key[source_id]}
                    else:
                        ref = {"referenceId": source_id}
                    if filter_field:
                        ref["filterField"] = filter_field
                    field["reference"] = ref
                lookup_id = field.pop("_lookupId", None)
                lookup_source = field.pop("_lookupSourceField", None)
                lookup_filter = field.pop("_lookupFilterField", None)
                if lookup_id and lookup_id in lookup_id_to_key:
                    lookup_spec: dict[str, Any] = {"lookup": lookup_id_to_key[lookup_id]}
                    if lookup_source:
                        lookup_spec["sourceField"] = lookup_source
                    if lookup_filter:
                        lookup_spec["filterField"] = lookup_filter
                    field["lookup"] = lookup_spec
            sections.append(
                {
                    "name": sec["name"],
                    "order": sec["order"],
                    "width": sec.get("width", 100),
                    "fields": sec["fields"],
                }
            )
        tab_out: dict[str, Any] = {
            "name": tab_data["name"],
            "placement": tab_data["placement"],
            "order": tab_data["order"],
            "sections": sections,
        }
        if tab_data.get("alwaysHidden"):
            tab_out["alwaysHidden"] = True
        tabs.append(tab_out)

    explicit_partial = {
        "tabs": explicit_tabs,
        "sections": explicit_sections,
        "fields": explicit_fields,
        "objectDefaultLines": explicit_default_lines,
        "lookups": explicit_lookups,
        "lookupValues": explicit_lookup_values,
        "references": explicit_sources,
        "sourceValues": explicit_source_values,
        "sourceRefObjects": explicit_ref_objects,
        "refObjectLines": explicit_ref_lines,
    }
    return tabs, explicit_partial, sources_spec, lookups_spec


def _build_ongrid(
    index: TransferIndex,
    object_id: int,
    field_codes: dict[int, str],
) -> tuple[dict | None, dict[str, int]]:
    og_fields: dict[str, dict] = {}
    for line in index.rows_for("ObjectLine", "ObjectID", object_id):
        line_id = int(line["ObjectLineID"])
        code = line.get("ObjectLineCode") or f"LINE_{line_id}"
        allowed = _boolish(line.get("ObjectLineOnGridIsAllowed"))
        is_tag = _boolish(line.get("ObjectLineOnGridIsTag"))
        is_search = _boolish(line.get("ObjectLineOnGridIsSearch"))
        is_total = _boolish(line.get("ObjectLineOnGridIsTotal"))
        if not (allowed or is_tag or is_search or is_total):
            continue
        entry: dict[str, Any] = {"allowed": allowed}
        if line.get("ObjectLineOnGridName"):
            entry["name"] = line["ObjectLineOnGridName"]
        if "ObjectLineOnGridIsTag" in line:
            entry["isTag"] = is_tag
        if is_search:
            entry["isSearch"] = True
        if is_total:
            entry["isTotal"] = True
        og_fields[str(code)] = entry

    layouts_map: dict[tuple, dict] = {}
    explicit_ongrid: dict[str, int] = {}

    for og in index.rows_for("ObjectLineOnGrid", "ObjectID", object_id):
        sys_id = _int(og.get("SystemLineID"))
        line_id = _int(og.get("ObjectLineID"))
        col: dict[str, Any] | None = None
        key_token: str | None = None
        if sys_id is not None:
            sys_code = code_for_id(sys_id)
            if not sys_code:
                continue
            key_token = explicit_key_token(sys_code)
            col = {"systemLine": sys_code}
        else:
            if line_id is None:
                continue
            ol = index.row_by_id("ObjectLine", line_id)
            if ol is not None and not _boolish(ol.get("ObjectLineOnGridIsAllowed")):
                continue
            code = field_codes.get(line_id)
            if not code:
                continue
            key_token = str(code)
            col = {"field": code}
        og_id = int(og["ObjectLineOnGridID"])
        size = og.get("ObjectLineOnGridSize", "Large")
        grid_type = og.get("ObjectLineOnGridType", "Grid")
        module = og.get("ObjectLineOnGridModule", "Items")
        explicit_ongrid[layout_id_key(size, grid_type, module, key_token)] = og_id
        layout = layouts_map.setdefault(
            (size, grid_type, module),
            {
                "size": size,
                "type": grid_type,
                "module": module,
                "placements": {},
            },
        )
        row_letter = og.get("ObjectLineOnGridRow", "T")
        placement = layout["placements"].setdefault(row_letter, {"row": row_letter, "columns": []})
        col.update(
            {
                "position": og.get("ObjectLineOnGridPosition", 1),
                "length": og.get("ObjectLineOnGridLength", 100),
                "valueWidth": og.get("ObjectLineOnGridValueWidth", 0),
                "labelType": og.get("ObjectLineOnGridLabelType", 1),
            }
        )
        placement["columns"].append(col)

    if not og_fields and not layouts_map:
        return None, explicit_ongrid

    layouts = []
    for layout in layouts_map.values():
        layout["placements"] = sorted(
            layout["placements"].values(),
            key=lambda p: p["row"],
        )
        for placement in layout["placements"]:
            placement["columns"].sort(key=lambda c: c.get("position", 0))
        layouts.append(layout)

    return {"fields": og_fields, "layouts": layouts}, explicit_ongrid


def _build_workflow(
    index: TransferIndex,
    template: dict | None,
    *,
    merge: dict | None = None,
    field_id_to_code: dict[int, str] | None = None,
    notification_id_to_key: dict[int, str] | None = None,
) -> tuple[dict | None, dict[str, Any], dict[str, dict], dict[str, dict]]:
    if not template:
        return None, {}, {}, {}

    wf_id = _int(template.get("WorkflowID"))
    if wf_id is None:
        return None, {}, {}, {}

    wf_row = index.row_by_id("Workflow", wf_id)
    if not wf_row:
        return None, {}, {}, {}

    steps = list(index.rows_for("WorkflowStep", "WorkflowID", wf_id))
    steps.sort(key=lambda r: r.get("WorkflowStepOrder", r.get("WorkflowStepID", 0)))

    actions_grouped = index.group_by("WorkflowStepAction", "WorkflowStepID")
    actions_by_step: dict[int, list[dict]] = {}
    for step in steps:
        sid = int(step["WorkflowStepID"])
        actions_by_step[sid] = list(actions_grouped.get(sid, []))

    role_ids, status_ids = _collect_role_status_ids(wf_row, steps, actions_by_step)
    roles, statuses, explicit_roles, explicit_statuses = _build_roles_statuses(
        index, role_ids, status_ids, merge
    )
    role_id_to_key = {v: k for k, v in explicit_roles.items()}
    status_id_to_key = {v: k for k, v in explicit_statuses.items()}

    explicit_steps: dict[str, int] = {}
    explicit_actions: dict[str, int] = {}
    explicit_step_access: dict[str, int] = {}
    explicit_step_notifs: dict[str, int] = {}
    step_specs = []

    step_name_counts = Counter(
        str(step.get("WorkflowStepName") or f"Step_{step['WorkflowStepID']}") for step in steps
    )
    action_name_counts: Counter[str] = Counter()
    for step in steps:
        for action in actions_by_step.get(int(step["WorkflowStepID"]), []):
            action_name_counts[
                str(action.get("WorkflowStepActionName") or f"Action_{action['WorkflowStepActionID']}")
            ] += 1

    used_step_keys: set[str] = set()
    used_action_keys: set[str] = set()
    step_id_to_key: dict[int, str] = {}

    for step in steps:
        step_id = int(step["WorkflowStepID"])
        step_name = str(step.get("WorkflowStepName") or f"Step_{step_id}")
        step_key = _disambiguate_key(
            used_step_keys, step_name, step_id, colliding=step_name_counts[step_name] > 1
        )
        step_id_to_key[step_id] = step_key
        explicit_steps[step_key] = step_id

        actions = actions_by_step.get(step_id, [])
        actions.sort(key=lambda r: r.get("WorkflowStepActionOrder", 10))

        action_specs = []
        for action in actions:
            action_id = int(action["WorkflowStepActionID"])
            action_name = str(action.get("WorkflowStepActionName") or f"Action_{action_id}")
            action_key = _disambiguate_key(
                used_action_keys,
                action_name,
                action_id,
                colliding=action_name_counts[action_name] > 1,
            )
            explicit_actions[action_key] = action_id
            role_key = role_id_to_key.get(int(action["RoleID"]))
            status_key = status_id_to_key.get(int(action["RequestStatusID"]))
            if role_key is None or status_key is None:
                continue
            action_spec: dict[str, Any] = {
                "name": action_name,
                "role": role_key,
                "status": status_key,
                "styleId": action.get("WorkflowStepActionStyleID", 1),
                "order": action.get("WorkflowStepActionOrder", 10),
            }
            if action_key != action_name:
                action_spec["key"] = action_key
            reopen = reopen_on_save_spec(action.get("WorkflowStepActionReopenTypeID"))
            if reopen:
                action_spec["reopenOnSave"] = reopen
            if not _boolish(action.get("IsActive", 1)):
                action_spec["isActive"] = False
            nid = _nid(action.get("NotificationID"))
            if nid and notification_id_to_key and nid in notification_id_to_key:
                action_spec["notification"] = notification_id_to_key[nid]
            action_specs.append(action_spec)

        step_role = role_id_to_key.get(int(step["RoleID"]))
        step_status = status_id_to_key.get(int(step["RequestStatusID"]))
        if step_role is None or step_status is None:
            continue
        step_spec: dict[str, Any] = {
            "name": step_name,
            "role": step_role,
            "status": step_status,
            "actions": action_specs,
        }
        if step_key != step_name:
            step_spec["key"] = step_key
        if _boolish(step.get("WorkflowStepIsSuppressSave", 0)):
            step_spec["suppressSave"] = True
        if not _boolish(step.get("IsActive", 1)):
            step_spec["isActive"] = False
        access_specs = _workflow_step_access_specs(
            index, step_id, step_key, field_id_to_code or {}, explicit_step_access
        )
        if access_specs:
            step_spec["access"] = access_specs
        step_notifs: list[str] = []
        notif_map = notification_id_to_key or {}
        for row in index.rows_for("WorkflowStepNotification", "WorkflowStepID", step_id):
            if not _boolish(row.get("IsActive", 1)):
                continue
            nid = _nid(row.get("NotificationID"))
            if not nid or nid not in notif_map:
                continue
            notif_key = notif_map[nid]
            explicit_step_notifs[step_notification_registry_key(step_key, notif_key)] = int(
                row["WorkflowStepNotificationID"]
            )
            step_notifs.append(notif_key)
        if step_notifs:
            step_spec["notifications"] = step_notifs
        step_specs.append(step_spec)

    step_names = tuple(s["name"] for s in step_specs)
    action_names = tuple(a["name"] for s in step_specs for a in s.get("actions", []))
    is_minimal = (
        len(step_specs) == 2
        and step_names == MINIMAL_STEP_NAMES
        and action_names == MINIMAL_ACTION_NAMES
        and not explicit_step_access
        and not explicit_step_notifs
        and not any(a.get("notification") for s in step_specs for a in s.get("actions") or [])
        and not any(_nid(wf_row.get(col)) for _spec_field, col in WORKFLOW_NOTIFICATION_FIELDS)
    )

    if is_minimal:
        workflow = {
            "mode": "minimal",
            "name": wf_row.get("WorkflowName"),
        }
    else:
        workflow = {
            "mode": "full",
            "name": wf_row.get("WorkflowName"),
            "steps": step_specs,
        }

    notif_map = notification_id_to_key or {}
    for spec_field, column in WORKFLOW_NOTIFICATION_FIELDS:
        nid = _nid(wf_row.get(column))
        if nid and nid in notif_map:
            workflow[spec_field] = notif_map[nid]

    explicit = {
        "workflowId": wf_id,
        "workflowSteps": explicit_steps,
        "workflowStepActions": explicit_actions,
        "objectDefaultId": int(template["ObjectDefaultID"]),
        "objectDefaultExternalLink": template.get("ObjectDefaultExternalLink"),
        "objectDefaultAccessOwnerLevel": int(template.get("ObjectDefaultAccessOwnerLevel", 0)),
        "objectDefaultIsExternal": int(template.get("ObjectDefaultIsExternal", 0)),
        "roles": explicit_roles,
        "statuses": explicit_statuses,
    }
    if explicit_step_access:
        explicit["workflowStepAccess"] = explicit_step_access
    if explicit_step_notifs:
        explicit["workflowStepNotifications"] = explicit_step_notifs
    return workflow, explicit, roles, statuses


def _workflow_step_access_specs(
    index: TransferIndex,
    step_id: int,
    step_name: str,
    field_id_to_code: dict[int, str],
    explicit_step_access: dict[str, int],
) -> list[dict[str, Any]]:
    access_specs: list[dict[str, Any]] = []
    for access in index.rows_for("WorkflowStepAccess", "WorkflowStepID", step_id):
        if not _boolish(access.get("IsActive", 1)):
            continue
        line_id = int(access["ObjectLineID"])
        field_code = _line_field_code(index, line_id, field_id_to_code)
        if not field_code:
            continue
        subline_id = _int(access.get("ObjectSubLineID"))
        access_id = int(access["WorkflowStepAccessID"])
        explicit_step_access[step_access_registry_key(step_name, field_code, subline_id)] = access_id
        if not step_access_differs_from_default(access):
            continue
        entry: dict[str, Any] = {
            "field": field_code,
            "editable": _boolish(access.get("WorkflowStepAccessIsEditable", 0)),
            "visible": _boolish(access.get("WorkflowStepAccessIsVisible", 1)),
        }
        if subline_id is not None:
            entry["sublineId"] = subline_id
        access_specs.append(entry)
    return access_specs


def _line_field_code(index: TransferIndex, line_id: int, field_id_to_code: dict[int, str]) -> str | None:
    if line_id in field_id_to_code:
        return field_id_to_code[line_id]
    line = index.row_by_id("ObjectLine", line_id)
    if not line:
        return None
    code = line.get("ObjectLineCode")
    if code:
        return str(code)
    return f"line_{line_id}"


def _tab_name(index: TransferIndex, tab_id: int | None) -> str | None:
    if tab_id is None:
        return None
    row = index.row_by_id("ObjectLineTab", int(tab_id))
    return row.get("ObjectLineTabName") if row else None


def _build_update_actions(
    index: TransferIndex,
    object_id: int,
    field_id_to_code: dict[int, str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    actions_rows = [
        row
        for row in index.rows_for("ObjectUpdateAction", "ObjectID", object_id)
        if _boolish(row.get("IsActive", 1))
    ]
    if not actions_rows:
        return [], {}

    actions_rows.sort(key=lambda r: (r.get("ObjectUpdateActionOrder", 10), r.get("ObjectUpdateActionID", 0)))

    default_by_id = {
        int(row["ObjectDefaultID"]): row.get("ObjectDefaultName", f"template_{row['ObjectDefaultID']}")
        for row in index.rows_for("ObjectDefault", "ObjectID", object_id)
    }
    workflow_by_id = {
        int(row["WorkflowID"]): row.get("WorkflowName", f"workflow_{row['WorkflowID']}")
        for row in index.rows.get("Workflow", [])
    }

    used_keys: set[str] = set()
    update_actions: list[dict[str, Any]] = []
    explicit: dict[str, Any] = {
        "updateActions": {},
        "objectUpdateAccess": {},
        "objectUpdateActionConditions": {},
        "objectUpdateMessages": {},
    }

    for row in actions_rows:
        action_id = int(row["ObjectUpdateActionID"])
        base_key = slugify(str(row.get("ObjectUpdateActionName", f"action_{action_id}")))
        key = base_key
        n = 2
        while key in used_keys:
            key = f"{base_key}_{n}"
            n += 1
        used_keys.add(key)
        explicit["updateActions"][key] = action_id

        spec_action: dict[str, Any] = {
            "key": key,
            "name": row.get("ObjectUpdateActionName", key),
            "order": row.get("ObjectUpdateActionOrder", 10),
        }

        default_id = row.get("ObjectDefaultID")
        if default_id is not None:
            spec_action["template"] = _slug(str(default_by_id.get(int(default_id), default_id)))

        wf_id = row.get("WorkflowID")
        if wf_id is not None:
            wf_name = workflow_by_id.get(int(wf_id))
            if wf_name:
                spec_action["workflow"] = _slug(wf_name)

        if _boolish(row.get("ObjectUpdateActionIsQuick", 0)):
            spec_action["isQuick"] = True
        reopen = reopen_on_save_spec(row.get("ObjectUpdateActionReopenTypeID"))
        if reopen:
            spec_action["reopenOnSave"] = reopen

        left = _tab_name(index, _int(row.get("ObjectLineTabFocusLeftID")))
        right = _tab_name(index, _int(row.get("ObjectLineTabFocusRightID")))
        if left or right:
            spec_action["tabFocus"] = {"left": left, "right": right}

        access_specs = []
        for access in index.rows_for("ObjectUpdateAccess", "ObjectUpdateActionID", action_id):
            if not _boolish(access.get("IsActive", 1)):
                continue
            if not access_differs_from_default(access):
                continue
            line_id = int(access["ObjectLineID"])
            field_code = _line_field_code(index, line_id, field_id_to_code)
            if not field_code:
                continue
            subline_id = _int(access.get("ObjectSubLineID"))
            access_id = int(access["ObjectUpdateAccessID"])
            reg_key = access_registry_key(key, field_code, subline_id)
            explicit["objectUpdateAccess"][reg_key] = access_id
            entry: dict[str, Any] = {
                "field": field_code,
                "editable": _boolish(access.get("ObjectLineIsEditableUpdate", 0)),
                "visible": _boolish(access.get("ObjectLineIsVisibleUpdate", 1)),
            }
            if subline_id is not None:
                entry["sublineId"] = subline_id
            access_specs.append(entry)
        if access_specs:
            spec_action["access"] = access_specs

        condition_specs = []
        for cond in index.rows_for(
            "ObjectUpdateActionCondition", "ObjectUpdateActionID", action_id
        ):
            if not _boolish(cond.get("IsActive", 1)):
                continue
            type_slug = condition_slug(int(cond.get("ObjectUpdateActionConditionTypeID", 0)))
            if not type_slug:
                continue
            line_id = int(cond["ObjectLineID"])
            field_code = _line_field_code(index, line_id, field_id_to_code)
            if not field_code:
                continue
            cond_id = int(cond["ObjectUpdateActionConditionID"])
            reg_key = f"{key}/{field_code}/{type_slug}"
            explicit["objectUpdateActionConditions"][reg_key] = cond_id
            entry = {"field": field_code, "type": type_slug}
            if cond.get("ObjectUpdateActionConditionParam1") is not None:
                entry["param1"] = cond["ObjectUpdateActionConditionParam1"]
            if cond.get("ObjectUpdateActionConditionParam2") is not None:
                entry["param2"] = cond["ObjectUpdateActionConditionParam2"]
            condition_specs.append(entry)
        if condition_specs:
            spec_action["conditions"] = condition_specs

        message_specs = []
        for msg_row in index.rows_for("ObjectUpdateMessage", "ObjectUpdateActionID", action_id):
            if not _boolish(msg_row.get("IsActive", 1)):
                continue
            om_id = int(msg_row["ObjectMessageID"])
            om = index.row_by_id("ObjectMessage", om_id)
            msg_key = message_key(om, om_id)
            explicit.setdefault("objectMessages", {})[msg_key] = om_id
            msg_id = int(msg_row["ObjectUpdateMessageID"])
            reg_key = f"{key}/{msg_key}"
            explicit["objectUpdateMessages"][reg_key] = msg_id
            message_specs.append(
                {
                    "key": msg_key,
                    "visible": _boolish(msg_row.get("ObjectUpdateMessageIsVisible", 0)),
                }
            )
        if message_specs:
            spec_action["messages"] = message_specs

        update_actions.append(spec_action)

    return update_actions, explicit


def _build_object_messages(
    index: TransferIndex,
    object_id: int,
    field_id_to_code: dict[int, str],
) -> tuple[list[dict], dict[str, Any]]:
    rows = [
        row
        for row in index.rows_for("ObjectMessage", "ObjectID", object_id)
        if _boolish(row.get("IsActive", 1))
    ]
    if not rows:
        return [], {}

    rows.sort(key=lambda r: (r.get("ObjectMessageOrder", 0), r.get("ObjectMessageID", 0)))
    used_keys: set[str] = set()
    messages: list[dict[str, Any]] = []
    explicit: dict[str, Any] = {"objectMessages": {}, "objectMessageConditions": {}}

    for row in rows:
        om_id = int(row["ObjectMessageID"])
        base_key = message_key(row, om_id)
        key = base_key
        n = 2
        while key in used_keys:
            key = f"{base_key}_{n}"
            n += 1
        used_keys.add(key)
        explicit["objectMessages"][key] = om_id
        spec_msg: dict[str, Any] = {
            "key": key,
            "name": row.get("ObjectMessageName", key),
            "style": style_slug(int(row.get("ObjectMessageStyleID", 1))),
            "order": row.get("ObjectMessageOrder", 10),
            "html": html_from_row(row),
        }
        conditions = []
        for cond in index.rows_for("ObjectMessageCondition", "ObjectMessageID", om_id):
            if not _boolish(cond.get("IsActive", 1)):
                continue
            type_slug = condition_slug(int(cond.get("ObjectMessageConditionTypeID", 0)))
            if not type_slug:
                continue
            line_id = int(cond["ObjectLineID"])
            field_code = _line_field_code(index, line_id, field_id_to_code)
            if not field_code:
                continue
            cond_id = int(cond["ObjectMessageConditionID"])
            explicit["objectMessageConditions"][
                object_message_condition_registry_key(key, field_code, type_slug)
            ] = cond_id
            entry: dict[str, Any] = {"field": field_code, "type": type_slug}
            if cond.get("ObjectMessageConditionParam1") is not None:
                entry["param1"] = cond["ObjectMessageConditionParam1"]
            if cond.get("ObjectMessageConditionParam2") is not None:
                entry["param2"] = cond["ObjectMessageConditionParam2"]
            conditions.append(entry)
        if conditions:
            spec_msg["conditions"] = conditions
        messages.append(spec_msg)

    return messages, explicit


def _all_templates(index: TransferIndex, object_id: int) -> list[dict]:
    defaults = [
        row
        for row in index.rows_for("ObjectDefault", "ObjectID", object_id)
        if _boolish(row.get("IsActive", 1))
    ]
    defaults.sort(
        key=lambda r: (
            0 if _boolish(r.get("ObjectDefaultIsDefault")) else 1,
            r.get("ObjectDefaultOrder", 0),
            r.get("ObjectDefaultID", 0),
        )
    )
    return defaults


def _template_has_extended(row: dict) -> bool:
    if _int(row.get("ObjectDefaultLineValidationID")) == 9:
        return True
    if row.get("ObjectDefaultLineClientCalculationTypeID"):
        return True
    if row.get("ObjectDefaultLineClientCalculation"):
        return True
    if row.get("ObjectDefaultLineValue"):
        return True
    if row.get("ObjectDefaultLineDescMemo"):
        return True
    if str(row.get("ObjectDefaultLineIsDisabled")) in ("1", "True", "true"):
        return True
    if row.get("ObjectDefaultLineAutoNumberID"):
        return True
    if row.get("ObjectDefaultLineHint"):
        return True
    return any(
        row.get(col)
        for col in (
            "ObjectDefaultLineValidationExtHiddenCondition",
            "ObjectDefaultLineValidationExtDisabledCondition",
            "ObjectDefaultLineValidationExtMandatoryCondition",
        )
    )


def _used_autonumber_ids(index: TransferIndex, object_id: int) -> set[int]:
    template_ids = {
        int(row["ObjectDefaultID"]) for row in _all_templates(index, object_id)
    }
    used: set[int] = set()
    for tid in template_ids:
        for tl in index.rows_for("ObjectDefaultLine", "ObjectDefaultID", tid):
            autonumber_id = _int(tl.get("ObjectDefaultLineAutoNumberID"))
            if autonumber_id:
                used.add(autonumber_id)
    return used


def _build_templates_spec(
    index: TransferIndex,
    object_id: int,
    field_id_to_code: dict[int, str],
    sources_spec: dict[str, dict],
    autonumber_id_to_key: dict[int, str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any], bool]:
    defaults = _all_templates(index, object_id)
    if not defaults:
        return [], {}, False

    used_keys: set[str] = set()
    templates: list[dict[str, Any]] = []
    explicit: dict[str, Any] = {
        "templates": {},
        "objectDefaultLines": {},
        "objectDefaultExternalLinks": {},
        "objectDefaultAccess": {},
    }
    any_extended = False
    any_access = False
    any_reopen = False
    legacy = len(defaults) <= 1

    for row in defaults:
        template_id = int(row["ObjectDefaultID"])
        name = str(row.get("ObjectDefaultName") or f"template_{template_id}")
        base_key = template_slug_from_name(name, template_id)
        key = base_key
        n = 2
        while key in used_keys:
            key = f"{base_key}_{n}"
            n += 1
        used_keys.add(key)
        explicit["templates"][key] = template_id
        if row.get("ObjectDefaultExternalLink"):
            explicit["objectDefaultExternalLinks"][key] = row["ObjectDefaultExternalLink"]

        spec_tmpl: dict[str, Any] = {
            "key": key,
            "name": name,
            "order": row.get("ObjectDefaultOrder", 0),
        }
        if _boolish(row.get("ObjectDefaultIsDefault")):
            spec_tmpl["isDefault"] = True
        access_owner = _int(row.get("ObjectDefaultAccessOwnerLevel"))
        if access_owner:
            spec_tmpl["accessOwnerLevel"] = access_owner
        if _boolish(row.get("ObjectDefaultIsExternal")):
            spec_tmpl["isExternal"] = 1
        if row.get("ObjectDefaultExternalLink"):
            spec_tmpl["externalLink"] = row["ObjectDefaultExternalLink"]
        reopen = reopen_on_save_spec(row.get("ObjectDefaultReopenTypeID"))
        if reopen:
            spec_tmpl["reopenOnSave"] = reopen
            any_reopen = True

        fields_spec: dict[str, Any] = {}
        for tl in index.rows_for("ObjectDefaultLine", "ObjectDefaultID", template_id):
            if not _boolish(tl.get("IsActive", 1)):
                continue
            line_id = int(tl["ObjectLineID"])
            field_code = field_id_to_code.get(line_id)
            if not field_code:
                continue
            if _template_has_extended(tl):
                any_extended = True
            explicit["objectDefaultLines"][
                template_line_key(key, field_code, legacy=legacy)
            ] = int(tl["ObjectDefaultLineID"])
            field_cfg = template_field_spec_from_line(
                tl, field_id_to_code, sources_spec, autonumber_id_to_key
            )
            if field_cfg:
                fields_spec[field_code] = field_cfg
        if fields_spec:
            spec_tmpl["fields"] = fields_spec

        access_specs: list[dict[str, Any]] = []
        for access in index.rows_for("ObjectDefaultAccess", "ObjectDefaultID", template_id):
            if not _boolish(access.get("IsActive", 1)):
                continue
            if not template_access_differs_from_default(access):
                continue
            line_id = int(access["ObjectLineID"])
            field_code = _line_field_code(index, line_id, field_id_to_code)
            if not field_code:
                continue
            subline_id = _int(access.get("ObjectSubLineID"))
            access_id = int(access["ObjectDefaultAccessID"])
            reg_key = template_access_registry_key(
                key, field_code, subline_id, legacy=legacy
            )
            explicit["objectDefaultAccess"][reg_key] = access_id
            entry: dict[str, Any] = {
                "field": field_code,
                "editable": _boolish(access.get("ObjectLineIsEditableCreate", 1)),
                "visible": _boolish(access.get("ObjectLineIsVisibleCreate", 1)),
            }
            if subline_id is not None:
                entry["sublineId"] = subline_id
            access_specs.append(entry)
        if access_specs:
            spec_tmpl["access"] = access_specs
            any_access = True

        templates.append(spec_tmpl)

    emit = len(templates) > 1 or any_extended or any_access or any_reopen
    return templates, explicit, emit


def _build_object_actions(
    index: TransferIndex,
    object_id: int,
    field_id_to_code: dict[int, str],
    step_id_to_key: dict[int, str] | None = None,
    role_id_to_key: dict[int, str] | None = None,
    status_id_to_key: dict[int, str] | None = None,
    notification_id_to_key: dict[int, str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    actions_rows = [
        row
        for row in index.rows_for("ObjectAction", "ObjectID", object_id)
        if _boolish(row.get("IsActive", 1))
    ]
    if not actions_rows:
        return [], {}

    actions_rows.sort(key=lambda r: (r.get("ObjectActionOrder", 10), r.get("ObjectActionID", 0)))
    step_key_by_id = dict(step_id_to_key or {})

    used_keys: set[str] = set()
    object_actions: list[dict[str, Any]] = []
    explicit: dict[str, Any] = {
        "objectActions": {},
        "objectActionParams": {},
        "objectActionConditions": {},
        "workflowStepObjectActions": {},
    }

    for row in actions_rows:
        action_id = int(row["ObjectActionID"])
        base_key = slugify(str(row.get("ObjectActionName", f"action_{action_id}")))
        key = base_key
        n = 2
        while key in used_keys:
            key = f"{base_key}_{n}"
            n += 1
        used_keys.add(key)
        explicit["objectActions"][key] = action_id

        spec_action: dict[str, Any] = {
            "key": key,
            "name": row.get("ObjectActionName", key),
            "typeCode": row.get("ObjectActionTypeCode"),
            "order": row.get("ObjectActionOrder", 10),
        }

        params: dict[str, Any] = {}
        for param in index.rows_for("ObjectActionParam", "ObjectActionID", action_id):
            if not _boolish(param.get("IsActive", 1)):
                continue
            param_code = str(param.get("ObjectActionTypeParamCode") or "")
            if not param_code:
                continue
            param_id = int(param["ObjectActionParamID"])
            explicit["objectActionParams"][param_registry_key(key, param_code)] = param_id
            params[param_code] = param_spec_value(
                param_code,
                param.get("ObjectActionParamValue"),
                field_id_to_code,
                role_id_to_key=role_id_to_key,
                status_id_to_key=status_id_to_key,
                notification_id_to_key=notification_id_to_key,
            )
        if params:
            spec_action["params"] = params

        conditions = []
        for cond in index.rows_for("ObjectActionCondition", "ObjectActionID", action_id):
            if not _boolish(cond.get("IsActive", 1)):
                continue
            type_slug = condition_slug(int(cond.get("ObjectActionConditionTypeID", 0)))
            if not type_slug:
                continue
            line_id = int(cond["ObjectLineID"])
            field_code = _line_field_code(index, line_id, field_id_to_code)
            if not field_code:
                continue
            cond_id = int(cond["ObjectActionConditionID"])
            explicit["objectActionConditions"][condition_registry_key(key, field_code, type_slug)] = cond_id
            entry: dict[str, Any] = {"field": field_code, "type": type_slug}
            if cond.get("ObjectActionConditionParam1") is not None:
                entry["param1"] = cond["ObjectActionConditionParam1"]
            if cond.get("ObjectActionConditionParam2") is not None:
                entry["param2"] = cond["ObjectActionConditionParam2"]
            conditions.append(entry)
        if conditions:
            spec_action["conditions"] = conditions

        step_names = []
        for link in index.rows_for("WorkflowStepObjectAction", "ObjectActionID", action_id):
            if not _boolish(link.get("IsActive", 1)):
                continue
            step_id = int(link["WorkflowStepID"])
            step_key = step_key_by_id.get(step_id)
            if not step_key:
                wf_step = index.row_by_id("WorkflowStep", step_id)
                if wf_step:
                    step_key = str(wf_step.get("WorkflowStepName") or f"step_{step_id}")
                    step_key_by_id[step_id] = step_key
            if not step_key:
                continue
            link_id = int(link["WorkflowStepObjectActionID"])
            explicit["workflowStepObjectActions"][step_link_registry_key(key, step_key)] = link_id
            step_names.append(step_key)
        if step_names:
            spec_action["workflowSteps"] = step_names

        object_actions.append(spec_action)

    return object_actions, explicit


def extract_spec_from_index(
    index: TransferIndex,
    obj: dict,
    *,
    source_path: Path | str,
    merge: dict | None = None,
    include_subtree_ids: bool = True,
    table_max_ids: dict[str, int] | None = None,
) -> dict:
    oid = int(obj["ObjectID"])
    mapping = _load_field_mapping()
    type_map = _type_id_to_spec(mapping)

    template = _default_template(index, oid)
    template_lines = _template_lines(index, int(template["ObjectDefaultID"])) if template else {}

    tabs, layout_explicit, sources_spec, lookups_spec = _build_layout(index, oid, template_lines, type_map)
    field_id_to_code = {int(v): k for k, v in layout_explicit["fields"].items()}
    autonumbers_spec, explicit_autonumbers = _build_autonumbers(
        index, _used_autonumber_ids(index, oid)
    )
    autonumber_id_to_key = {row_id: key for key, row_id in explicit_autonumbers.items()}
    ongrid, ongrid_explicit = _build_ongrid(index, oid, field_id_to_code)
    notifications, n_explicit, notification_id_to_key = extract_notifications(
        index,
        oid,
        _int(template.get("WorkflowID")) if template else None,
        field_id_to_code,
        _line_field_code,
    )
    workflow, wf_explicit, roles, statuses = _build_workflow(
        index,
        template,
        merge=merge,
        field_id_to_code=field_id_to_code,
        notification_id_to_key=notification_id_to_key,
    )
    update_actions, ua_explicit = _build_update_actions(index, oid, field_id_to_code)
    object_messages, om_explicit = _build_object_messages(index, oid, field_id_to_code)
    templates, tmpl_explicit, emit_templates = _build_templates_spec(
        index, oid, field_id_to_code, sources_spec, autonumber_id_to_key
    )
    object_actions, oa_explicit = _build_object_actions(
        index,
        oid,
        field_id_to_code,
        step_id_to_key={int(v): k for k, v in (wf_explicit.get("workflowSteps") or {}).items()},
        role_id_to_key={int(v): k for k, v in (wf_explicit.get("roles") or {}).items()},
        status_id_to_key={int(v): k for k, v in (wf_explicit.get("statuses") or {}).items()},
        notification_id_to_key=notification_id_to_key,
    )
    periodics, pe_explicit = extract_periodics(
        index,
        oid,
        field_id_to_code,
        _line_field_code,
        role_id_to_key={int(v): k for k, v in (wf_explicit.get("roles") or {}).items()},
        status_id_to_key={int(v): k for k, v in (wf_explicit.get("statuses") or {}).items()},
        notification_id_to_key=notification_id_to_key,
    )

    ot_id = int(obj["ObjectTypeID"])
    ot_row = index.row_by_id("ObjectType", ot_id)
    object_type_name = ot_row.get("ObjectTypeName", "General") if ot_row else "General"

    by_table = _collect_subtree_ids(index, oid) if include_subtree_ids else {}
    company_id = int(obj.get("CompanyID", 1))
    company_row = index.row_by_id("Company", company_id)
    if company_row and company_row.get("CompanyName"):
        company_name = company_row.get("CompanyName", "")
    else:
        company_name = f"Company {company_id}"

    explicit: dict[str, Any] = {
        "companyId": company_id,
        "objectTypeId": ot_id,
        "objectId": oid,
        **layout_explicit,
        **wf_explicit,
        **ua_explicit,
        **om_explicit,
        **oa_explicit,
        **pe_explicit,
        **n_explicit,
        "objectLineOnGrid": ongrid_explicit,
    }
    if explicit_autonumbers:
        explicit["autonumbers"] = explicit_autonumbers
    if emit_templates:
        explicit["templates"] = tmpl_explicit.get("templates") or {}
        explicit["objectDefaultLines"] = tmpl_explicit.get("objectDefaultLines") or {}
        if tmpl_explicit.get("objectDefaultAccess"):
            explicit["objectDefaultAccess"] = tmpl_explicit["objectDefaultAccess"]
        if tmpl_explicit.get("objectDefaultExternalLinks"):
            explicit["objectDefaultExternalLinks"] = tmpl_explicit["objectDefaultExternalLinks"]
        for field in (
            field
            for tab in tabs
            for section in tab.get("sections") or []
            for field in section.get("fields") or []
        ):
            field.pop("mandatory", None)

    base_ids = table_max_ids if table_max_ids is not None else collect_table_max_ids(index)
    spec: dict[str, Any] = {
        "version": 2,
        "kind": "create_object",
        "transferType": "object",
        "object": {
            "name": obj["ObjectName"],
            "code": obj.get("ObjectCode"),
            "objectType": object_type_name,
        },
        "company": {"name": company_name},
        "layout": {"tabs": tabs},
        "ids": {
            "base": base_ids or 9000,
            "explicit": explicit,
            "byTable": by_table,
        },
        "transferVersion": (index.transfer_info or {}).get("Version", "1.3.0"),
        "source": {
            "transfer": str(source_path),
            "objectId": oid,
            "objectCode": obj.get("ObjectCode"),
            "extractedAt": date.today().isoformat(),
        },
    }

    obj_icon = _nonempty_str(obj, "ObjectTreeIcon")
    if obj_icon:
        spec["object"]["icon"] = obj_icon
    obj_color = _nonempty_str(obj, "ObjectTreeColor")
    if obj_color:
        spec["object"]["color"] = obj_color

    object_type_spec: dict[str, Any] = {}
    ot_icon = _nonempty_str(ot_row, "ObjectTypeTreeIcon")
    if ot_icon:
        object_type_spec["icon"] = ot_icon
    ot_color = _nonempty_str(ot_row, "ObjectTypeTreeColorBack")
    if ot_color:
        object_type_spec["color"] = ot_color
    if object_type_spec:
        spec["objectType"] = object_type_spec

    company_icon = _nonempty_str(company_row, "CompanyTreeIcon")
    if company_icon:
        spec["company"]["icon"] = company_icon

    title_line_id = _int(obj.get("RequestTitleObjectLineID"))
    if title_line_id is not None:
        title_code = _object_line_code(index, title_line_id)
        if title_code:
            spec["object"]["requestTitleField"] = title_code

    sort_line_id = _int(obj.get("ObjectGridSortObjectLineID"))
    sort_type = (_nonempty_str(obj, "ObjectGridSortType") or "").upper()
    if sort_line_id is not None and sort_type in ("ASC", "DESC"):
        sort_code = _object_line_code(index, sort_line_id)
        if sort_code:
            spec["object"]["gridSort"] = {"field": sort_code, "type": sort_type}

    if ongrid:
        spec["onGrid"] = ongrid
    if sources_spec:
        spec["references"] = sources_spec
    if lookups_spec:
        spec["lookups"] = lookups_spec
    if autonumbers_spec:
        spec["autonumbers"] = autonumbers_spec
    if roles:
        spec["roles"] = roles
    if statuses:
        spec["statuses"] = statuses
    if workflow:
        spec["workflow"] = workflow
    if update_actions:
        spec["updateActions"] = update_actions
    if object_messages:
        spec["objectMessages"] = object_messages
    if emit_templates:
        spec["templates"] = templates
    if object_actions:
        spec["objectActions"] = object_actions
    if periodics:
        spec["periodics"] = periodics
    if notifications:
        spec["notifications"] = notifications

    language_table, lt_explicit = extract_language_table(index, explicit)
    if language_table:
        spec["languageTable"] = language_table
        explicit["languageTables"] = lt_explicit
        spec["ids"]["explicit"] = explicit

    comments, tc_explicit = extract_comments(index, explicit)
    if comments:
        spec["comments"] = comments
        explicit["tableComments"] = tc_explicit
        spec["ids"]["explicit"] = explicit

    if merge:
        spec = _merge_spec(merge, spec)

    return spec


def extract_spec(
    path: Path,
    *,
    object_id: int | None = None,
    object_code: str | None = None,
    object_name: str | None = None,
    merge: dict | None = None,
) -> dict:
    parsed = load_transfer(path)
    obj = find_object_row(parsed, object_id=object_id, object_code=object_code, object_name=object_name)
    index = TransferIndex.from_parsed(parsed)
    return extract_spec_from_index(index, obj, source_path=path, merge=merge)


def _merge_spec(base: dict, extracted: dict) -> dict:
    merged = dict(base)
    for key in (
        "layout",
        "onGrid",
        "workflow",
        "updateActions",
        "objectMessages",
        "objectActions",
        "periodics",
        "notifications",
        "templates",
        "objectDefault",
        "roles",
        "statuses",
        "references",
        "sources",
        "lookups",
        "autonumbers",
        "languageTable",
        "comments",
        "object",
        "objectType",
        "company",
        "ids",
        "source",
    ):
        if key in extracted:
            if key == "ids" and key in merged:
                merged_ids = dict(merged["ids"])
                merged_ids.update(extracted["ids"])
                if "explicit" in extracted["ids"]:
                    merged_ids["explicit"] = {**merged.get("ids", {}).get("explicit", {}), **extracted["ids"]["explicit"]}
                if "byTable" in extracted["ids"]:
                    merged_ids["byTable"] = extracted["ids"]["byTable"]
                merged["ids"] = merged_ids
            else:
                merged[key] = extracted[key]
    return merged
