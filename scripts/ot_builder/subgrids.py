"""ObjectSub trees: emit Object Transfer rows and extract spec/subgrids.yaml."""

from __future__ import annotations

from typing import Any

from ot_builder.ids import IdRegistry
from ot_builder.ongrid import (
    DEFAULT_MODULE,
    DEFAULT_SIZE,
    DEFAULT_TYPE,
    require_subgrid_ongrid_id,
)
from ot_builder.parse import TransferIndex
from ot_builder.spec_loader import spec_references
from ot_builder.templates import (
    CLIENT_CALC_ID_TYPES,
    COMBO_FIELD_TYPES,
    LOOKUP_FIELD_TYPES,
    PLACEHOLDER_CALC_TYPES,
    PLACEHOLDER_PARAM_RE,
    REFERENCE_FIELD_TYPES,
    SUBGRID_CLIENT_CALC_TYPE_IDS,
    VALIDATION_MANDATORY,
    VALIDATION_OPTIONAL,
    compile_extended_condition,
    decompile_extended_condition,
    field_lookup_key,
    iter_layout_fields,
    slugify,
)

# ObjectSubWidth = add/edit-row modal width (%). Admin 50–100; default 80.
DEFAULT_WIDTH = 80
UNSUPPORTED_SUBGRID_TYPES = frozenset({"subgrid", "report", "button"})
NO_SLOT_SUBGRID_TYPES = frozenset({"empty_space", "description_memo", "attachment_preview"})

# Re-export-friendly slug (same as extract._slug / update_actions.slugify).
def _slug(name: str) -> str:
    return slugify(name) or "item"


def subgrid_tab_key(sub_key: str, tab_name: str) -> str:
    return f"{sub_key}/{tab_name}"


def subgrid_section_key(sub_key: str, tab_name: str, section_name: str) -> str:
    return f"{sub_key}/{tab_name}/{section_name}"


def subgrid_field_key(sub_key: str, field_code: str) -> str:
    return f"{sub_key}/{field_code}"


def subgrid_template_key(sub_key: str, template_key: str) -> str:
    return f"{sub_key}/{template_key}"


def subgrid_default_line_key(sub_key: str, template_key: str, field_code: str) -> str:
    return f"{sub_key}/{template_key}/{field_code}"


def resolve_parent_object_sub_id(field: dict[str, Any], spec: dict, registry: IdRegistry) -> int | None:
    """ObjectLine.ObjectSubID from objectSub key (emit tree) or objectSubId (reuse/share)."""
    key = field.get("objectSub")
    if key:
        key_s = str(key)
        if key_s not in (spec.get("subgrids") or {}):
            raise ValueError(
                f"Field {field.get('code')!r} objectSub {key_s!r} is not in spec subgrids: "
                "(add the tree, or use objectSubId to bind an existing shared ObjectSub)"
            )
        return registry.require("subgrids", key_s)
    if field.get("objectSubId") is not None:
        return int(field["objectSubId"])
    return None


def _layout_fields_by_code(spec: dict) -> dict[str, dict[str, Any]]:
    return {str(f.get("code")): f for f in iter_layout_fields(spec) if f.get("code")}


def subgrid_column_ids_for_field(field: dict[str, Any], spec: dict, registry: IdRegistry) -> list[int]:
    """ObjectSubLine IDs for a parent type-5 field with objectSub: (spec tree)."""
    if field.get("type") != "subgrid":
        return []
    sub_key = field.get("objectSub")
    if not sub_key:
        return []
    sub_def = (spec.get("subgrids") or {}).get(str(sub_key)) or {}
    ids: list[int] = []
    for tab in (sub_def.get("layout") or {}).get("tabs") or []:
        for section in tab.get("sections") or []:
            for col in section.get("fields") or []:
                code = col.get("code")
                if not code:
                    continue
                ids.append(registry.require("subgridFields", subgrid_field_key(str(sub_key), str(code))))
    return ids


def resolve_access_subline_id(
    access: dict[str, Any],
    field: dict[str, Any],
    spec: dict,
    registry: IdRegistry,
) -> int | None:
    """ObjectSubLineID from access.sublineId or access.subline (column code)."""
    if access.get("sublineId") is not None:
        return int(access["sublineId"])
    sub_code = access.get("subline")
    if not sub_code:
        return None
    sub_key = field.get("objectSub")
    if not sub_key:
        raise ValueError(
            f"access field {access.get('field')!r} subline {sub_code!r} requires parent objectSub"
        )
    return registry.require("subgridFields", subgrid_field_key(str(sub_key), str(sub_code)))


def with_subgrid_column_access(
    access_items: list[dict[str, Any]],
    spec: dict,
    registry: IdRegistry,
    *,
    default_editable: bool,
) -> list[tuple[dict[str, Any], int | None]]:
    """Parent type-5 access plus implied ObjectSubLine rows.

    A row without ObjectSubLineID is the subgrid widget. The add/edit-row modal
    uses per-column access; Object Transfer does not run Admin refresh, so missing
    column rows hide every ObjectSubLine. Copy parent flags onto columns not
    listed; type-5 fields with no access item still get columns at
    visible=true / default_editable.
    """
    fields = _layout_fields_by_code(spec)
    resolved: list[tuple[dict[str, Any], int | None]] = []
    have: set[tuple[str, int | None]] = set()
    for item in access_items or []:
        code = str(item["field"])
        field = fields.get(code) or {}
        sub_id = resolve_access_subline_id(item, field, spec, registry)
        resolved.append((item, sub_id))
        have.add((code, sub_id))

    parent_flags: dict[str, dict[str, Any]] = {}
    for item, sub_id in resolved:
        if sub_id is None:
            parent_flags[str(item["field"])] = item

    extras: list[tuple[dict[str, Any], int | None]] = []
    for code, field in fields.items():
        col_ids = subgrid_column_ids_for_field(field, spec, registry)
        if not col_ids:
            continue
        flags = parent_flags.get(code)
        if flags is None:
            col_item: dict[str, Any] = {
                "field": code,
                "visible": True,
                "editable": default_editable,
            }
        else:
            col_item = {
                "field": code,
                "visible": flags.get("visible", True),
                "editable": flags.get("editable", False),
            }
        for col_id in col_ids:
            if (code, col_id) not in have:
                extras.append((col_item, col_id))
                have.add((code, col_id))
    return resolved + extras


def _apply_subline_ongrid_flags(line_row: dict[str, Any], og_field: dict[str, Any]) -> None:
    """ObjectSubLine display flags from subgrids.<key>.onGrid.fields.<code>."""
    if not og_field:
        return
    if "allowed" in og_field:
        line_row["ObjectSubLineOnGridIsAllowed"] = 1 if og_field.get("allowed") else 0
    else:
        line_row["ObjectSubLineOnGridIsAllowed"] = 1
    if og_field.get("name"):
        line_row["ObjectSubLineOnGridName"] = og_field["name"]
    if "isTag" in og_field:
        line_row["ObjectSubLineOnGridIsTag"] = 1 if og_field["isTag"] else 0
    if og_field.get("isSearch"):
        line_row["ObjectSubLineIsSearch"] = 1
    if og_field.get("isTotal"):
        line_row["ObjectSubLineIsTotal"] = 1


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


def _apply_subline_extras(
    line_row: dict[str, Any],
    field: dict[str, Any],
    ftype: str,
    *,
    sub_key: str,
    code_f: str,
) -> None:
    """Type extras on ObjectSubLine — same spec keys as ObjectLine, ObjectSubLine* columns."""
    line_row["ObjectSubLineIsEditable"] = 1
    if ftype == "number":
        if field.get("precision") is None:
            raise ValueError(
                f"subgrids.{sub_key} field {code_f!r} type number requires precision "
                "(ObjectSubLineNumberPrecision; without it values do not store)"
            )
        line_row["ObjectSubLineNumberPrecision"] = int(field["precision"])
        if field.get("numberSeparator") is not None:
            line_row["ObjectSubLineNumberSeparator"] = str(field["numberSeparator"])
        if field.get("numberMin") is not None:
            line_row["ObjectSubLineNumberMin"] = int(field["numberMin"])
        if field.get("numberMax") is not None:
            line_row["ObjectSubLineNumberMax"] = int(field["numberMax"])
    if ftype == "text" and field.get("textInputType") is not None:
        line_row["ObjectSubLineTextInputType"] = int(field["textInputType"])
    if ftype in ("radio", "checkbox_multiselect") and field.get("columnNumbers") is not None:
        line_row["ObjectSubLineNumberColumns"] = int(field["columnNumbers"])
    if ftype == "web_frame" and field.get("webFrameTypeId") is not None:
        line_row["WebFrameTypeID"] = int(field["webFrameTypeId"])
    if ftype == "memo" and field.get("height") is not None:
        line_row["ObjectSubLineHeight"] = int(field["height"])
    if ftype == "description_memo":
        if field.get("descMemoBorder") is not None:
            line_row["ObjectSubLineDescMemoIsBorder"] = 1 if field.get("descMemoBorder") else 0
        if field.get("descMemoPadding") is not None:
            line_row["ObjectSubLineDescMemoPadding"] = int(field["descMemoPadding"])
    if ftype in COMBO_FIELD_TYPES and field.get("isReferenceLink") is not None:
        line_row["ObjectSubLineIsReferenceLink"] = 1 if field.get("isReferenceLink") else 0
    if ftype == "attachment":
        if field.get("attachmentStorageId") is None:
            raise ValueError(
                f"subgrids.{sub_key} field {code_f!r} type attachment requires attachmentStorageId"
            )
        line_row["AttachmentStorageID"] = int(field["attachmentStorageId"])
        if field.get("ocr") is not None:
            line_row["ObjectSubLineAttachmentIsOCR"] = 1 if field.get("ocr") else 0
        if field.get("ocrLang") is not None:
            line_row["ObjectSubLineAttachmentOCRLang"] = str(field["ocrLang"])
        if field.get("imageResizeMax") is not None:
            line_row["ObjectSubLineAttachmentImageResizeMax"] = int(field["imageResizeMax"])
        if field.get("mobileScan") is not None:
            line_row["ObjectSubLineAttachmentMobileIsScan"] = 1 if field.get("mobileScan") else 0
        if field.get("mobileSignature") is not None:
            line_row["ObjectSubLineAttachmentMobileIsSignature"] = (
                1 if field.get("mobileSignature") else 0
            )


def _bind_subline_cross_fields(
    line_row: dict[str, Any],
    field: dict[str, Any],
    ftype: str,
    *,
    sub_key: str,
    code_f: str,
    spec: dict,
    registry: IdRegistry,
    field_by_code: dict[str, dict],
    result: Any,
) -> None:
    """reference / previewField — resolve other ObjectSubLine codes in this tree."""
    if ftype in REFERENCE_FIELD_TYPES:
        reference = field.get("reference")
        if not isinstance(reference, dict):
            raise ValueError(
                f"subgrids.{sub_key} field {code_f!r} type {ftype} requires reference"
            )
        source_id = _resolve_source_id(spec, registry, reference)
        line_row["ObjectSubLineSourceID"] = source_id
        result.edges.append(
            {
                "TableName": "ObjectSubLine",
                "TableRowID": line_row["ObjectSubLineID"],
                "ChildTableName": "ObjectLineSource",
                "ChildTableRowID": source_id,
            }
        )
        filter_field = reference.get("filterField")
        if filter_field:
            if str(filter_field) not in field_by_code:
                raise ValueError(
                    f"subgrids.{sub_key} field {code_f!r} filterField {filter_field!r} "
                    "is not a column in this objectSub"
                )
            line_row["ObjectSubLineSourceFilterObjectSubLineID"] = registry.require(
                "subgridFields", subgrid_field_key(str(sub_key), str(filter_field))
            )
    if ftype == "attachment_preview":
        preview_field = field.get("previewField")
        if not preview_field:
            raise ValueError(
                f"subgrids.{sub_key} field {code_f!r} type attachment_preview requires previewField"
            )
        if str(preview_field) not in field_by_code:
            raise ValueError(
                f"subgrids.{sub_key} field {code_f!r} previewField {preview_field!r} "
                "is not a column in this objectSub"
            )
        line_row["ObjectSubLineAttPreviewObjectSubLineID"] = registry.require(
            "subgridFields", subgrid_field_key(str(sub_key), str(preview_field))
        )
        if field.get("previewDownload") is not None:
            line_row["ObjectSubLineAttPreviewIsDownload"] = (
                1 if field.get("previewDownload") else 0
            )


def _apply_sub_default_line_lookup_calc(
    dl_row: dict[str, Any],
    field: dict[str, Any],
    cfg: dict[str, Any],
    *,
    sub_key: str,
    code_f: str,
    spec: dict,
    registry: IdRegistry,
    result: Any,
) -> None:
    """Lookup + client calc on ObjectSubDefaultLine (same spec keys as ObjectDefaultLine)."""
    ftype = str(field.get("type") or "")
    if cfg.get("alwaysDisabled"):
        dl_row["ObjectSubDefaultLineIsDisabled"] = 1
    lookup = field.get("lookup")
    if isinstance(lookup, dict) and ftype in LOOKUP_FIELD_TYPES:
        source_field = lookup.get("sourceField")
        if not source_field:
            raise ValueError(
                f"subgrids.{sub_key} field {code_f!r} lookup requires sourceField"
            )
        lookup_key = field_lookup_key(field, lookup)
        lookup_id = registry.require("lookups", lookup_key)
        dl_row["ObjectSubDefaultLineLookupID"] = lookup_id
        dl_row["ObjectSubDefaultLineLookupObjectSubLineID"] = registry.require(
            "subgridFields", subgrid_field_key(str(sub_key), str(source_field))
        )
        filter_field = lookup.get("filterField")
        if filter_field:
            dl_row["ObjectSubDefaultLineLookupFilterObjectSubLineID"] = registry.require(
                "subgridFields", subgrid_field_key(str(sub_key), str(filter_field))
            )
        result.edges.append(
            {
                "TableName": "ObjectSubDefaultLine",
                "TableRowID": dl_row["ObjectSubDefaultLineID"],
                "ChildTableName": "ObjectLineLookup",
                "ChildTableRowID": lookup_id,
            }
        )
    calc = cfg.get("clientCalculation")
    if not isinstance(calc, dict) or not calc.get("type"):
        return
    type_slug = str(calc["type"])
    if type_slug not in SUBGRID_CLIENT_CALC_TYPE_IDS:
        raise ValueError(
            f"subgrids.{sub_key} field {code_f!r} clientCalculation.type {type_slug!r} "
            "is not on ObjectSubLineCalculationType (no focus or device_info)"
        )
    dl_row["ObjectSubDefaultLineClientCalculationTypeID"] = SUBGRID_CLIENT_CALC_TYPE_IDS[
        type_slug
    ]
    expr = calc.get("expr")
    if type_slug in PLACEHOLDER_CALC_TYPES:
        expr_str = "" if expr is None else str(expr).strip()
        if not PLACEHOLDER_PARAM_RE.fullmatch(expr_str):
            raise ValueError(
                f"clientCalculation.type {type_slug!r} requires expr as a single {{Placeholder}}"
            )
        expr = expr_str
    if expr is not None and str(expr) != "":
        def resolve_id(code: str) -> int:
            return registry.require("subgridFields", subgrid_field_key(str(sub_key), code))

        dl_row["ObjectSubDefaultLineClientCalculation"] = compile_extended_condition(
            str(expr), spec, registry, resolve_id=resolve_id
        )


def emit_subgrids(spec: dict, registry: IdRegistry, mapping: dict, result: Any) -> None:
    """Emit ObjectSub* rows for spec['subgrids']. Call before parent ObjectLine rows."""
    subgrids = spec.get("subgrids") or {}
    if not subgrids:
        return

    sub_rows: list[dict] = []
    tab_rows: list[dict] = []
    section_rows: list[dict] = []
    line_rows: list[dict] = []
    default_rows: list[dict] = []
    default_line_rows: list[dict] = []
    ongrid_rows: list[dict] = []

    for sub_key, sub_def in subgrids.items():
        if not isinstance(sub_def, dict):
            raise ValueError(f"subgrids.{sub_key} must be a mapping")
        sub_id = registry.require("subgrids", str(sub_key))
        name = sub_def.get("name") or str(sub_key)
        sub_row: dict[str, Any] = {
            "ObjectSubID": sub_id,
            "ObjectSubName": name,
            "ObjectSubWidth": int(sub_def.get("width") or DEFAULT_WIDTH),
            "IsActive": 1,
        }
        code = sub_def.get("code")
        if code:
            sub_row["ObjectSubCode"] = str(code)
        sub_rows.append(sub_row)

        layout = sub_def.get("layout") or {}
        tabs = layout.get("tabs") or []
        if not tabs:
            raise ValueError(f"subgrids.{sub_key} requires layout.tabs")

        field_codes: list[str] = []
        field_by_code: dict[str, dict] = {}
        pending_lines: list[tuple[dict[str, Any], dict[str, Any], str, str]] = []
        line_index = 0
        for tab in tabs:
            tab_name = tab["name"]
            tab_id = registry.require("subgridTabs", subgrid_tab_key(str(sub_key), tab_name))
            tab_rows.append(
                {
                    "ObjectSubLineTabID": tab_id,
                    "ObjectSubLineTabName": tab_name,
                    "ObjectSubLineTabOrder": tab.get("order", 1),
                    "ObjectSubLineTabPlacement": tab.get("placement", 0),
                    "IsActive": 1,
                }
            )
            for section in tab.get("sections") or []:
                section_name = section["name"]
                sec_id = registry.require(
                    "subgridSections",
                    subgrid_section_key(str(sub_key), tab_name, section_name),
                )
                section_rows.append(
                    {
                        "ObjectSubLineSectionID": sec_id,
                        "ObjectSubSectionName": section_name,
                        "ObjectSubSectionOrder": section.get("order", 1),
                        "ObjectSubSectionWidth": section.get("width", 100),
                        "ObjectSubLineTabID": tab_id,
                        "IsActive": 1,
                    }
                )
                result.edges.append(
                    {
                        "TableName": "ObjectSubLineTab",
                        "TableRowID": tab_id,
                        "ChildTableName": "ObjectSubLineSection",
                        "ChildTableRowID": sec_id,
                    }
                )
                for field in section.get("fields") or []:
                    line_index += 1
                    ftype = field["type"]
                    code_f = str(field.get("code") or f"SUB_{line_index}")
                    if ftype not in mapping:
                        raise ValueError(
                            f"subgrids.{sub_key} unknown field type {ftype!r}"
                        )
                    if ftype in UNSUPPORTED_SUBGRID_TYPES:
                        raise ValueError(
                            f"subgrids.{sub_key} field {code_f!r} type {ftype!r} "
                            "is not on ObjectSubLineType (no nested subgrid, report, or button)"
                        )
                    type_info = mapping[ftype]
                    field_codes.append(code_f)
                    field_by_code[code_f] = field
                    line_id = registry.require(
                        "subgridFields", subgrid_field_key(str(sub_key), code_f)
                    )
                    line_row: dict[str, Any] = {
                        "ObjectSubID": sub_id,
                        "ObjectSubLineID": line_id,
                        "ObjectSubLineSectionID": sec_id,
                        "ObjectSubLineName": field["name"],
                        "ObjectSubLineOrder": field.get("order", line_index * 10),
                        "ObjectSubLineTypeID": type_info["objectLineTypeId"],
                        "ObjectSubLineTypeWidth": field.get("width", 100),
                        "IsActive": 1 if field.get("isActive", True) else 0,
                    }
                    if field.get("slot") is not None:
                        line_row["ObjectSubLineSlot"] = int(field["slot"])
                    elif ftype not in NO_SLOT_SUBGRID_TYPES:
                        line_row["ObjectSubLineSlot"] = line_index
                    if field.get("code"):
                        line_row["ObjectSubLineCode"] = field["code"]
                    _apply_subline_extras(
                        line_row, field, ftype, sub_key=str(sub_key), code_f=code_f
                    )
                    og_spec = sub_def.get("onGrid") if isinstance(sub_def.get("onGrid"), dict) else {}
                    _apply_subline_ongrid_flags(line_row, (og_spec.get("fields") or {}).get(code_f) or {})
                    line_rows.append(line_row)
                    pending_lines.append((line_row, field, ftype, code_f))
                    result.edges.extend(
                        [
                            {
                                "TableName": "ObjectSub",
                                "TableRowID": sub_id,
                                "ChildTableName": "ObjectSubLine",
                                "ChildTableRowID": line_id,
                            },
                            {
                                "TableName": "ObjectSubLine",
                                "TableRowID": line_id,
                                "ChildTableName": "ObjectSubLineTab",
                                "ChildTableRowID": tab_id,
                            },
                        ]
                    )

        for line_row, field, ftype, code_f in pending_lines:
            _bind_subline_cross_fields(
                line_row,
                field,
                ftype,
                sub_key=str(sub_key),
                code_f=code_f,
                spec=spec,
                registry=registry,
                field_by_code=field_by_code,
                result=result,
            )

        templates = list(sub_def.get("templates") or [])
        if not templates:
            templates = [{"key": "default", "name": "Default", "isDefault": True}]
        default_seen = False
        for index, template_cfg in enumerate(templates):
            tpl_key = str(
                template_cfg.get("key") or slugify(str(template_cfg.get("name", "default")))
            )
            is_default = bool(template_cfg.get("isDefault")) or (not default_seen and index == 0)
            if is_default:
                default_seen = True
            tpl_id = registry.require("subgridTemplates", subgrid_template_key(str(sub_key), tpl_key))
            default_rows.append(
                {
                    "ObjectSubID": sub_id,
                    "ObjectSubDefaultID": tpl_id,
                    "ObjectSubDefaultName": template_cfg.get("name") or tpl_key,
                    "ObjectSubDefaultIsDefault": 1 if is_default else 0,
                    "IsActive": 1,
                }
            )
            result.edges.append(
                {
                    "TableName": "ObjectSub",
                    "TableRowID": sub_id,
                    "ChildTableName": "ObjectSubDefault",
                    "ChildTableRowID": tpl_id,
                }
            )
            tpl_fields = template_cfg.get("fields") or {}
            for code_f in field_codes:
                field = field_by_code[code_f]
                line_id = registry.require(
                    "subgridFields", subgrid_field_key(str(sub_key), code_f)
                )
                dl_id = registry.require(
                    "subgridDefaultLines",
                    subgrid_default_line_key(str(sub_key), tpl_key, code_f),
                )
                field_cfg = tpl_fields.get(code_f) if isinstance(tpl_fields, dict) else None
                cfg = field_cfg if isinstance(field_cfg, dict) else {}
                mandatory = cfg.get("mandatory", field.get("mandatory"))
                dl_row: dict[str, Any] = {
                    "ObjectSubDefaultID": tpl_id,
                    "ObjectSubDefaultLineID": dl_id,
                    "ObjectSubLineID": line_id,
                    "ObjectSubDefaultLineValidationID": (
                        VALIDATION_MANDATORY if mandatory else VALIDATION_OPTIONAL
                    ),
                    "IsActive": 1,
                }
                hint = cfg.get("hint")
                if hint is not None and str(hint).strip() != "":
                    dl_row["ObjectSubDefaultLineHint"] = str(hint)
                autonumber_key = cfg.get("autonumber") or field.get("autonumber")
                if autonumber_key:
                    if field.get("type") != "text":
                        raise ValueError(
                            f"subgrids.{sub_key} field {code_f!r} autonumber requires type text"
                        )
                    an_id = registry.require("autonumbers", str(autonumber_key))
                    dl_row["ObjectSubDefaultLineAutoNumberID"] = an_id
                    result.edges.append(
                        {
                            "TableName": "ObjectSubDefaultLine",
                            "TableRowID": dl_id,
                            "ChildTableName": "ObjectLineAutoNumber",
                            "ChildTableRowID": an_id,
                        }
                    )
                _apply_sub_default_line_lookup_calc(
                    dl_row,
                    field,
                    cfg,
                    sub_key=str(sub_key),
                    code_f=code_f,
                    spec=spec,
                    registry=registry,
                    result=result,
                )
                default_line_rows.append(dl_row)
                result.edges.append(
                    {
                        "TableName": "ObjectSubDefault",
                        "TableRowID": tpl_id,
                        "ChildTableName": "ObjectSubDefaultLine",
                        "ChildTableRowID": dl_id,
                    }
                )

        og_spec = sub_def.get("onGrid") if isinstance(sub_def.get("onGrid"), dict) else {}
        used_legacy_ongrid: set[str] = set()
        for og_layout in og_spec.get("layouts") or []:
            size = og_layout.get("size") or DEFAULT_SIZE
            grid_type = og_layout.get("type") or DEFAULT_TYPE
            module = og_layout.get("module") or DEFAULT_MODULE
            for placement in og_layout.get("placements") or []:
                row_letter = placement.get("row", "T")
                for col in placement.get("columns") or []:
                    if col.get("systemLine"):
                        raise ValueError(
                            f"subgrids.{sub_key} onGrid has no systemLine "
                            "(ObjectSubLineOnGrid has ObjectSubLineID only)"
                        )
                    field_code = col.get("field")
                    if not field_code:
                        raise ValueError(f"subgrids.{sub_key} onGrid column needs field")
                    if str(field_code) not in field_by_code:
                        raise ValueError(
                            f"subgrids.{sub_key} onGrid unknown field {field_code!r}"
                        )
                    line_id = registry.require(
                        "subgridFields", subgrid_field_key(str(sub_key), str(field_code))
                    )
                    og_id = require_subgrid_ongrid_id(
                        registry,
                        sub_key=str(sub_key),
                        size=size,
                        grid_type=grid_type,
                        module=module,
                        field_code=str(field_code),
                        used_legacy=used_legacy_ongrid,
                    )
                    ongrid_rows.append(
                        {
                            "ObjectSubLineOnGridID": og_id,
                            "ObjectSubLineID": line_id,
                            "ObjectSubLineOnGridSize": size,
                            "ObjectSubLineOnGridType": grid_type,
                            "ObjectSubLineOnGridModule": module,
                            "ObjectSubLineOnGridRow": row_letter,
                            "ObjectSubLineOnGridPosition": col.get("position", 1),
                            "ObjectSubLineOnGridLength": col.get("length", 100),
                            "ObjectSubLineOnGridValueWidth": col.get("valueWidth", 0),
                            "ObjectSubLineOnGridLabelType": col.get("labelType", 1),
                            "IsActive": 1,
                        }
                    )
                    result.edges.append(
                        {
                            "TableName": "ObjectSubLine",
                            "TableRowID": line_id,
                            "ChildTableName": "ObjectSubLineOnGrid",
                            "ChildTableRowID": og_id,
                        }
                    )

    if sub_rows:
        result.rows["ObjectSub"] = sub_rows
    if tab_rows:
        result.rows["ObjectSubLineTab"] = tab_rows
    if section_rows:
        result.rows["ObjectSubLineSection"] = section_rows
    if line_rows:
        result.rows["ObjectSubLine"] = line_rows
    if default_rows:
        result.rows["ObjectSubDefault"] = default_rows
    if default_line_rows:
        result.rows["ObjectSubDefaultLine"] = default_line_rows
    if ongrid_rows:
        result.rows["ObjectSubLineOnGrid"] = ongrid_rows


def bind_parent_subgrid_template(
    template_line: dict[str, Any],
    *,
    field: dict[str, Any],
    template_field: dict[str, Any] | None,
    spec: dict,
    registry: IdRegistry,
) -> None:
    """ObjectDefaultLine.ObjectSubDefaultID from templates.fields.<code>.subgridTemplate."""
    if field.get("type") != "subgrid":
        return
    cfg = dict(template_field or {})
    tpl_key = cfg.get("subgridTemplate")
    if not tpl_key:
        return
    sub_key = field.get("objectSub")
    if not sub_key:
        raise ValueError(
            f"Field {field.get('code')!r} subgridTemplate requires objectSub (spec subgrids key)"
        )
    template_line["ObjectSubDefaultID"] = registry.require(
        "subgridTemplates", subgrid_template_key(str(sub_key), str(tpl_key))
    )


def _int(val: Any) -> int | None:
    if val is None:
        return None
    return int(val)


def _boolish(val: Any) -> bool:
    return str(val) in ("1", "True", "true")


def _emit_true(field: dict[str, Any], key: str, value: Any) -> None:
    if _boolish(value):
        field[key] = True


def _apply_extracted_subline_extras(
    field: dict[str, Any],
    line: dict[str, Any],
    ftype: str,
    line_id_to_code: dict[int, str],
) -> None:
    """Same spec keys as ObjectLine extras; ObjectSubLine* columns. Preview via subgrid codes."""
    if ftype == "number":
        if line.get("ObjectSubLineNumberSeparator"):
            field["numberSeparator"] = line["ObjectSubLineNumberSeparator"]
        number_min = _int(line.get("ObjectSubLineNumberMin"))
        if number_min is not None:
            field["numberMin"] = number_min
        number_max = _int(line.get("ObjectSubLineNumberMax"))
        if number_max is not None:
            field["numberMax"] = number_max
    if ftype == "text":
        text_input = _int(line.get("ObjectSubLineTextInputType"))
        if text_input:
            field["textInputType"] = text_input
    if ftype in ("radio", "checkbox_multiselect"):
        columns = _int(line.get("ObjectSubLineNumberColumns"))
        if columns is not None and columns != 1:
            field["columnNumbers"] = columns
    if ftype == "web_frame":
        web_frame = _int(line.get("WebFrameTypeID"))
        if web_frame:
            field["webFrameTypeId"] = web_frame
    if ftype == "memo":
        height = _int(line.get("ObjectSubLineHeight"))
        if height:
            field["height"] = height
    if ftype == "description_memo":
        _emit_true(field, "descMemoBorder", line.get("ObjectSubLineDescMemoIsBorder"))
        padding = _int(line.get("ObjectSubLineDescMemoPadding"))
        if padding is not None:
            field["descMemoPadding"] = padding
    if ftype in COMBO_FIELD_TYPES:
        _emit_true(field, "isReferenceLink", line.get("ObjectSubLineIsReferenceLink"))
    if ftype == "attachment":
        storage_id = _int(line.get("AttachmentStorageID"))
        if storage_id is not None:
            field["attachmentStorageId"] = storage_id
        _emit_true(field, "ocr", line.get("ObjectSubLineAttachmentIsOCR"))
        if line.get("ObjectSubLineAttachmentOCRLang"):
            field["ocrLang"] = line["ObjectSubLineAttachmentOCRLang"]
        resize = _int(line.get("ObjectSubLineAttachmentImageResizeMax"))
        if resize:
            field["imageResizeMax"] = resize
        _emit_true(field, "mobileScan", line.get("ObjectSubLineAttachmentMobileIsScan"))
        _emit_true(field, "mobileSignature", line.get("ObjectSubLineAttachmentMobileIsSignature"))
    if ftype == "attachment_preview":
        preview_id = _int(line.get("ObjectSubLineAttPreviewObjectSubLineID"))
        preview_code = line_id_to_code.get(preview_id) if preview_id is not None else None
        if preview_code:
            field["previewField"] = preview_code
        if line.get("ObjectSubLineAttPreviewIsDownload") is not None and not _boolish(
            line.get("ObjectSubLineAttPreviewIsDownload")
        ):
            field["previewDownload"] = False


def bind_extracted_subgrid_references(
    subgrids_spec: dict[str, Any],
    source_id_to_key: dict[int, str],
) -> None:
    """Turn stashed ObjectSubLineSourceID into spec reference keys."""
    for tree in (subgrids_spec or {}).values():
        if not isinstance(tree, dict):
            continue
        for tab in (tree.get("layout") or {}).get("tabs") or []:
            for section in tab.get("sections") or []:
                for field in section.get("fields") or []:
                    source_id = field.pop("_sourceId", None)
                    filter_field = field.pop("_filterField", None)
                    if not source_id:
                        continue
                    if source_id in source_id_to_key:
                        ref: dict[str, Any] = {"reference": source_id_to_key[source_id]}
                    else:
                        ref = {"referenceId": source_id}
                    if filter_field:
                        ref["filterField"] = filter_field
                    field["reference"] = ref


def bind_extracted_subgrid_lookups(
    subgrids_spec: dict[str, Any],
    lookup_id_to_key: dict[int, str],
) -> None:
    """Turn stashed ObjectSubDefaultLineLookupID into spec lookup keys."""
    for tree in (subgrids_spec or {}).values():
        if not isinstance(tree, dict):
            continue
        for tab in (tree.get("layout") or {}).get("tabs") or []:
            for section in tab.get("sections") or []:
                for field in section.get("fields") or []:
                    lookup_id = field.pop("_lookupId", None)
                    source_field = field.pop("_lookupSourceField", None)
                    filter_field = field.pop("_lookupFilterField", None)
                    if not lookup_id or lookup_id not in lookup_id_to_key:
                        continue
                    lookup_spec: dict[str, Any] = {"lookup": lookup_id_to_key[lookup_id]}
                    if source_field:
                        lookup_spec["sourceField"] = source_field
                    if filter_field:
                        lookup_spec["filterField"] = filter_field
                    field["lookup"] = lookup_spec


def bind_extracted_subgrid_calcs(
    subgrids_spec: dict[str, Any],
    subline_id_to_code: dict[int, str],
    sources_spec: dict[str, dict],
) -> None:
    """Decompile stashed ObjectSubDefaultLineClientCalculation using ObjectSubLine IDs."""
    for tree in (subgrids_spec or {}).values():
        if not isinstance(tree, dict):
            continue
        for tpl in tree.get("templates") or []:
            for cfg in (tpl.get("fields") or {}).values():
                if not isinstance(cfg, dict):
                    continue
                calc = cfg.get("clientCalculation")
                if not isinstance(calc, dict):
                    continue
                raw = calc.pop("_expr", None)
                if raw:
                    calc["expr"] = decompile_extended_condition(
                        str(raw), subline_id_to_code, sources_spec
                    )


def extract_subgrids_spec(
    index: TransferIndex,
    object_id: int,
    type_map: dict[int, str],
    autonumber_id_to_key: dict[int, str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[int, str], set[int], set[int]]:
    """Return (subgrids spec, explicit ids, ObjectSubID → key, used source IDs, used lookup IDs)."""
    sub_ids: set[int] = set()
    for row in index.rows_for("ObjectLine", "ObjectID", object_id):
        sid = _int(row.get("ObjectSubID"))
        if sid is not None:
            sub_ids.add(sid)
    if not sub_ids:
        return {}, {}, {}, set(), set()

    used_keys: set[str] = set()
    subgrids: dict[str, Any] = {}
    explicit: dict[str, Any] = {
        "subgrids": {},
        "subgridTabs": {},
        "subgridSections": {},
        "subgridFields": {},
        "subgridTemplates": {},
        "subgridDefaultLines": {},
        "subgridOnGrid": {},
    }
    id_to_key: dict[int, str] = {}
    used_source_ids: set[int] = set()
    used_lookup_ids: set[int] = set()

    for sub_id in sorted(sub_ids):
        sub = index.row_by_id("ObjectSub", sub_id)
        if not sub:
            continue
        raw_key = sub.get("ObjectSubCode") or sub.get("ObjectSubName") or str(sub_id)
        key = _slug(str(raw_key))
        if key in used_keys:
            key = f"{key}_{sub_id}"
        used_keys.add(key)
        id_to_key[sub_id] = key
        explicit["subgrids"][key] = sub_id

        lines = sorted(
            index.rows_for("ObjectSubLine", "ObjectSubID", sub_id),
            key=lambda r: (r.get("ObjectSubLineOrder") or 0, r.get("ObjectSubLineID") or 0),
        )
        section_ids: list[int] = []
        seen_sec: set[int] = set()
        for line in lines:
            ssid = _int(line.get("ObjectSubLineSectionID"))
            if ssid is not None and ssid not in seen_sec:
                seen_sec.add(ssid)
                section_ids.append(ssid)

        tabs_layout: dict[int, dict[str, Any]] = {}
        tab_order: list[int] = []
        for ssid in section_ids:
            sec = index.row_by_id("ObjectSubLineSection", ssid)
            if not sec:
                continue
            tab_id = _int(sec.get("ObjectSubLineTabID"))
            if tab_id is None:
                continue
            if tab_id not in tabs_layout:
                tab = index.row_by_id("ObjectSubLineTab", tab_id) or {}
                tab_name = tab.get("ObjectSubLineTabName") or f"Tab {tab_id}"
                tabs_layout[tab_id] = {
                    "name": tab_name,
                    "placement": tab.get("ObjectSubLineTabPlacement", 0),
                    "order": tab.get("ObjectSubLineTabOrder", 1),
                    "sections": {},
                }
                tab_order.append(tab_id)
                explicit["subgridTabs"][subgrid_tab_key(key, str(tab_name))] = tab_id
            tab_name = tabs_layout[tab_id]["name"]
            sec_name = sec.get("ObjectSubSectionName") or f"Section {ssid}"
            sec_key = subgrid_section_key(key, str(tab_name), str(sec_name))
            explicit["subgridSections"][sec_key] = ssid
            tabs_layout[tab_id]["sections"][ssid] = {
                "name": sec_name,
                "order": sec.get("ObjectSubSectionOrder", 1),
                "width": sec.get("ObjectSubSectionWidth") or 100,
                "fields": [],
            }

        line_id_to_code: dict[int, str] = {}
        layout_fields_by_code: dict[str, dict[str, Any]] = {}
        for line in lines:
            line_id = int(line["ObjectSubLineID"])
            code = line.get("ObjectSubLineCode") or f"SUBLINE_{line_id}"
            line_id_to_code[line_id] = str(code)

        for line in lines:
            line_id = int(line["ObjectSubLineID"])
            type_id = int(line.get("ObjectSubLineTypeID") or 3)
            ftype = type_map.get(type_id, "text")
            code = line_id_to_code[line_id]
            explicit["subgridFields"][subgrid_field_key(key, str(code))] = line_id
            field: dict[str, Any] = {
                "name": line.get("ObjectSubLineName", ""),
                "code": code,
                "type": ftype,
                "width": line.get("ObjectSubLineTypeWidth", 100),
                "order": line.get("ObjectSubLineOrder"),
            }
            slot = line.get("ObjectSubLineSlot")
            if slot is not None:
                field["slot"] = slot
            if ftype == "number" and line.get("ObjectSubLineNumberPrecision") is not None:
                field["precision"] = int(line["ObjectSubLineNumberPrecision"])
            _apply_extracted_subline_extras(field, line, ftype, line_id_to_code)
            source_id = _int(line.get("ObjectSubLineSourceID"))
            if source_id and ftype in REFERENCE_FIELD_TYPES:
                used_source_ids.add(source_id)
                field["_sourceId"] = source_id
            filter_line_id = _int(line.get("ObjectSubLineSourceFilterObjectSubLineID"))
            if filter_line_id is not None:
                filt_code = line_id_to_code.get(filter_line_id)
                if filt_code:
                    field["_filterField"] = filt_code
            if not _boolish(line.get("IsActive", 1)):
                field["isActive"] = False
            layout_fields_by_code[str(code)] = field
            ssid = _int(line.get("ObjectSubLineSectionID"))
            placed = False
            if ssid is not None:
                for tab_id in tab_order:
                    sec_entry = tabs_layout.get(tab_id, {}).get("sections", {}).get(ssid)
                    if sec_entry is not None:
                        sec_entry["fields"].append(field)
                        placed = True
                        break
            if not placed:
                if not tab_order:
                    tabs_layout[0] = {
                        "name": "General",
                        "placement": 0,
                        "order": 1,
                        "sections": {
                            0: {
                                "name": "Details",
                                "order": 1,
                                "width": 100,
                                "fields": [],
                            }
                        },
                    }
                    tab_order.append(0)
                first_tab = tabs_layout[tab_order[0]]
                first_sec = next(iter(first_tab["sections"].values()))
                first_sec["fields"].append(field)

        tab_list = []
        for tab_id in tab_order:
            entry = tabs_layout[tab_id]
            sections = [
                {
                    "name": sec["name"],
                    "order": sec["order"],
                    "width": sec["width"],
                    "fields": sec["fields"],
                }
                for sec in sorted(
                    entry["sections"].values(),
                    key=lambda s: (s.get("order") or 0),
                )
            ]
            tab_spec: dict[str, Any] = {
                "name": entry["name"],
                "placement": entry.get("placement", 0),
                "order": entry.get("order", 1),
                "sections": sections,
            }
            tab_list.append(tab_spec)

        spec_entry: dict[str, Any] = {
            "name": sub.get("ObjectSubName", ""),
            "width": sub.get("ObjectSubWidth") or DEFAULT_WIDTH,
            "layout": {"tabs": tab_list},
        }
        if sub.get("ObjectSubCode"):
            spec_entry["code"] = sub.get("ObjectSubCode")

        templates_spec: list[dict[str, Any]] = []
        defaults = [
            row
            for row in index.rows_for("ObjectSubDefault", "ObjectSubID", sub_id)
            if _boolish(row.get("IsActive", 1))
        ]
        defaults.sort(
            key=lambda r: (
                0 if _boolish(r.get("ObjectSubDefaultIsDefault")) else 1,
                r.get("ObjectSubDefaultID") or 0,
            )
        )
        for default in defaults:
            did = int(default["ObjectSubDefaultID"])
            tpl_name = default.get("ObjectSubDefaultName") or f"template_{did}"
            tpl_key = _slug(str(tpl_name))
            explicit["subgridTemplates"][subgrid_template_key(key, tpl_key)] = did
            tpl_fields: dict[str, Any] = {}
            for dl in index.rows_for("ObjectSubDefaultLine", "ObjectSubDefaultID", did):
                if not _boolish(dl.get("IsActive", 1)):
                    continue
                lid = _int(dl.get("ObjectSubLineID"))
                if lid is None:
                    continue
                code_f = line_id_to_code.get(lid) or f"SUBLINE_{lid}"
                explicit["subgridDefaultLines"][
                    subgrid_default_line_key(key, tpl_key, str(code_f))
                ] = int(dl["ObjectSubDefaultLineID"])
                cfg: dict[str, Any] = {}
                if _int(dl.get("ObjectSubDefaultLineValidationID")) == VALIDATION_MANDATORY:
                    cfg["mandatory"] = True
                hint = dl.get("ObjectSubDefaultLineHint")
                if hint is not None and str(hint).strip() != "":
                    cfg["hint"] = str(hint)
                an_id = _int(dl.get("ObjectSubDefaultLineAutoNumberID"))
                if an_id is not None and autonumber_id_to_key:
                    an_key = autonumber_id_to_key.get(an_id)
                    if an_key:
                        cfg["autonumber"] = an_key
                if _boolish(dl.get("ObjectSubDefaultLineIsDisabled")):
                    cfg["alwaysDisabled"] = True
                calc_type_id = _int(dl.get("ObjectSubDefaultLineClientCalculationTypeID"))
                calc_expr = dl.get("ObjectSubDefaultLineClientCalculation")
                if calc_type_id is not None:
                    type_slug = CLIENT_CALC_ID_TYPES.get(calc_type_id)
                    if type_slug:
                        calc_spec: dict[str, Any] = {"type": type_slug}
                        if calc_expr:
                            calc_spec["_expr"] = str(calc_expr)
                        cfg["clientCalculation"] = calc_spec
                layout_field = layout_fields_by_code.get(str(code_f))
                ftype = str((layout_field or {}).get("type") or "")
                lookup_id = _int(dl.get("ObjectSubDefaultLineLookupID"))
                if lookup_id and ftype in LOOKUP_FIELD_TYPES and layout_field is not None:
                    used_lookup_ids.add(lookup_id)
                    layout_field["_lookupId"] = lookup_id
                    src_code = line_id_to_code.get(
                        _int(dl.get("ObjectSubDefaultLineLookupObjectSubLineID")) or -1
                    )
                    if src_code:
                        layout_field["_lookupSourceField"] = src_code
                    filt_code = line_id_to_code.get(
                        _int(dl.get("ObjectSubDefaultLineLookupFilterObjectSubLineID")) or -1
                    )
                    if filt_code:
                        layout_field["_lookupFilterField"] = filt_code
                if cfg:
                    tpl_fields[str(code_f)] = cfg
            tpl_entry: dict[str, Any] = {
                "key": tpl_key,
                "name": tpl_name,
            }
            if _boolish(default.get("ObjectSubDefaultIsDefault")):
                tpl_entry["isDefault"] = True
            if tpl_fields:
                tpl_entry["fields"] = tpl_fields
            templates_spec.append(tpl_entry)
        if templates_spec:
            spec_entry["templates"] = templates_spec

        og_fields: dict[str, dict] = {}
        for line in lines:
            lid = int(line["ObjectSubLineID"])
            code_og = line_id_to_code.get(lid)
            if not code_og:
                continue
            allowed = _boolish(line.get("ObjectSubLineOnGridIsAllowed"))
            is_tag = _boolish(line.get("ObjectSubLineOnGridIsTag"))
            is_search = _boolish(line.get("ObjectSubLineIsSearch"))
            is_total = _boolish(line.get("ObjectSubLineIsTotal"))
            if not (allowed or is_tag or is_search or is_total):
                continue
            entry: dict[str, Any] = {"allowed": allowed}
            if line.get("ObjectSubLineOnGridName"):
                entry["name"] = line["ObjectSubLineOnGridName"]
            if "ObjectSubLineOnGridIsTag" in line:
                entry["isTag"] = is_tag
            if is_search:
                entry["isSearch"] = True
            if is_total:
                entry["isTotal"] = True
            og_fields[str(code_og)] = entry

        layouts_map: dict[tuple, dict] = {}
        explicit_ongrid: dict[str, int] = {}
        for line in lines:
            lid = int(line["ObjectSubLineID"])
            code_og = line_id_to_code.get(lid)
            if not code_og:
                continue
            if not _boolish(line.get("ObjectSubLineOnGridIsAllowed")):
                continue
            for og in index.rows_for("ObjectSubLineOnGrid", "ObjectSubLineID", lid):
                og_id = int(og["ObjectSubLineOnGridID"])
                size = og.get("ObjectSubLineOnGridSize", "Large")
                grid_type = og.get("ObjectSubLineOnGridType", "Grid")
                module = og.get("ObjectSubLineOnGridModule", "Items")
                explicit_ongrid[f"{key}/{size}/{grid_type}/{module}/{code_og}"] = og_id
                layout = layouts_map.setdefault(
                    (size, grid_type, module),
                    {
                        "size": size,
                        "type": grid_type,
                        "module": module,
                        "placements": {},
                    },
                )
                row_letter = og.get("ObjectSubLineOnGridRow", "T")
                placement = layout["placements"].setdefault(
                    row_letter, {"row": row_letter, "columns": []}
                )
                placement["columns"].append(
                    {
                        "field": code_og,
                        "position": og.get("ObjectSubLineOnGridPosition", 1),
                        "length": og.get("ObjectSubLineOnGridLength", 100),
                        "valueWidth": og.get("ObjectSubLineOnGridValueWidth", 0),
                        "labelType": og.get("ObjectSubLineOnGridLabelType", 1),
                    }
                )
        if og_fields or layouts_map:
            layouts = []
            for layout in layouts_map.values():
                layout["placements"] = sorted(
                    layout["placements"].values(),
                    key=lambda p: p["row"],
                )
                for placement in layout["placements"]:
                    placement["columns"].sort(key=lambda c: c.get("position", 0))
                layouts.append(layout)
            spec_entry["onGrid"] = {"fields": og_fields, "layouts": layouts}
        if explicit_ongrid:
            explicit.setdefault("subgridOnGrid", {}).update(explicit_ongrid)

        subgrids[key] = spec_entry

    # drop empty explicit maps
    explicit = {k: v for k, v in explicit.items() if v}
    return subgrids, explicit, id_to_key, used_source_ids, used_lookup_ids


def used_subgrid_autonumber_ids(index: TransferIndex, object_id: int) -> set[int]:
    used: set[int] = set()
    sub_ids: set[int] = set()
    for row in index.rows_for("ObjectLine", "ObjectID", object_id):
        sid = _int(row.get("ObjectSubID"))
        if sid is not None:
            sub_ids.add(sid)
    for sub_id in sub_ids:
        for default in index.rows_for("ObjectSubDefault", "ObjectSubID", sub_id):
            did = default.get("ObjectSubDefaultID")
            if did is None:
                continue
            for dl in index.rows_for("ObjectSubDefaultLine", "ObjectSubDefaultID", int(did)):
                an_id = _int(dl.get("ObjectSubDefaultLineAutoNumberID"))
                if an_id:
                    used.add(an_id)
    return used


def object_sub_default_id_to_template_key(
    index: TransferIndex,
    sub_id_to_key: dict[int, str],
) -> dict[int, str]:
    """ObjectSubDefaultID → templates[].subgridTemplate key (the template key only)."""
    out: dict[int, str] = {}
    for sub_id, _sub_key in sub_id_to_key.items():
        for default in index.rows_for("ObjectSubDefault", "ObjectSubID", sub_id):
            did = _int(default.get("ObjectSubDefaultID"))
            if did is None:
                continue
            tpl_name = default.get("ObjectSubDefaultName") or f"template_{did}"
            out[did] = _slug(str(tpl_name))
    return out
