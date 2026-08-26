"""Canonical YAML key order for xeelo-spec (matches OT extract insertion order).

Extract dumps with PyYAML ``sort_keys=False``, so git history stays quiet only when
agents write the same mapping order. ``write_spec`` and ``normalize-spec-yaml.py``
apply this module before dump. Unknown keys stay at the end (stable, never dropped).
"""

from __future__ import annotations

from typing import Any, Callable

from ot_builder.language_table import USER_LANGUAGE_CODES

# --- mapping key tuples (extract insertion order) ---

SPEC_TOP_KEYS = (
    "version",
    "kind",
    "transferType",
    "transferVersion",
    "object",
    "objectType",
    "company",
    "layout",
    "onGrid",
    "references",
    "lookups",
    "autonumbers",
    "objectServices",
    "languageTable",
    "comments",
    "roles",
    "statuses",
    "workflow",
    "templates",
    "objectDefault",
    "objectActions",
    "objectMessages",
    "updateActions",
    "periodics",
    "notifications",
    "subgrids",
    "ids",
    "source",
    "includes",
)

OBJECT_KEYS = (
    "name",
    "code",
    "objectType",
    "icon",
    "color",
    "requestTitleField",
    "gridSort",
)

OBJECT_TYPE_KEYS = ("icon", "color")
COMPANY_KEYS = ("name", "icon")
LAYOUT_KEYS = ("tabs",)
GRID_SORT_KEYS = ("field", "type")

TAB_KEYS = ("name", "placement", "order", "sections", "alwaysHidden")
SECTION_KEYS = ("name", "order", "width", "fields")

FIELD_KEYS = (
    "name",
    "code",
    "type",
    "width",
    "order",
    "slot",
    "precision",
    "objectSub",
    "objectSubId",
    "saveAction",
    "uniqueId",
    "numberSeparator",
    "numberMin",
    "numberMax",
    "textInputType",
    "columnNumbers",
    "webFrameTypeId",
    "height",
    "descMemoBorder",
    "descMemoPadding",
    "buttonMessage",
    "colorFont",
    "colorBack",
    "isReferenceLink",
    "attachmentStorageId",
    "ocr",
    "ocrLang",
    "imageResizeMax",
    "mobileScan",
    "mobileSignature",
    "previewField",
    "previewDownload",
    "alwaysHidden",
    "isActive",
    "mandatory",
    "reference",
    "lookup",
    "autonumber",
)

REFERENCE_BIND_KEYS = ("reference", "referenceId", "source", "sourceId", "filterField")
LOOKUP_BIND_KEYS = ("lookup", "name", "sourceField", "filterField", "matchId", "values")

REFERENCE_DEF_KEYS = ("name", "typeId", "styleId", "values", "refObject")
SOURCE_VALUE_KEYS = ("value", "label", "bind", "order")
SOURCE_REF_OBJECT_KEYS = ("objectId", "requestType", "name", "lines")
SOURCE_REF_LINES_KEYS = ("value", "valueName", "valueBind", "valueFilter", "valueOrder")

LOOKUP_DEF_KEYS = ("name", "values", "matchId")
LOOKUP_VALUE_KEYS = ("source", "return", "filter", "sourceTo", "label", "value")

AUTONUMBER_DEF_KEYS = ("description", "format", "next", "resetTypeId")
OBJECT_SERVICE_DEF_KEYS = ("name", "type", "link")

ONGRID_KEYS = ("fields", "layouts")
ONGRID_FIELD_KEYS = ("allowed", "name", "isTag", "isSearch", "isTotal")
ONGRID_LAYOUT_KEYS = ("size", "type", "module", "placements")
ONGRID_PLACEMENT_KEYS = ("row", "columns")
ONGRID_COLUMN_KEYS = (
    "field",
    "systemLine",
    "position",
    "length",
    "valueWidth",
    "labelType",
)

SUBGRID_KEYS = ("name", "width", "layout", "code", "templates", "onGrid")
SUBGRID_TEMPLATE_KEYS = ("key", "name", "isDefault", "fields")

ROLE_KEYS = ("name", "isRequestor", "isOwner", "isActive")
STATUS_KEYS = ("name", "order", "isCompleted", "isCanceled", "isActive")

WORKFLOW_KEYS = (
    "mode",
    "reuse",
    "name",
    "steps",
    "notification",
    "exportFailNotification",
    "recallNotification",
    "failNotification",
)
WORKFLOW_STEP_KEYS = (
    "name",
    "role",
    "status",
    "actions",
    "key",
    "suppressSave",
    "isActive",
    "access",
    "notifications",
)
WORKFLOW_STEP_ACTION_KEYS = (
    "name",
    "role",
    "status",
    "styleId",
    "order",
    "key",
    "reopenOnSave",
    "isActive",
    "notification",
)
ACCESS_LINE_KEYS = ("field", "editable", "visible", "sublineId")

TEMPLATE_KEYS = (
    "key",
    "name",
    "order",
    "isDefault",
    "accessOwnerLevel",
    "isExternal",
    "externalLink",
    "reopenOnSave",
    "fields",
    "access",
)
TEMPLATE_FIELD_KEYS = (
    "alwaysDisabled",
    "mandatory",
    "hidden",
    "extended",
    "defaultValue",
    "defaultFilter",
    "calcDelay",
    "calcConfirm",
    "clientCalculation",
    "autonumber",
    "subgridTemplate",
    "hint",
)
EXTENDED_KEYS = ("hidden", "disabled", "mandatory")
CLIENT_CALC_KEYS = ("type", "service", "expr")
OBJECT_DEFAULT_KEYS = ("name", "order", "accessOwnerLevel", "isExternal", "externalLink")

OBJECT_ACTION_KEYS = (
    "key",
    "name",
    "typeCode",
    "order",
    "params",
    "conditions",
    "workflowSteps",
    "isActive",
)
ACTION_CONDITION_KEYS = ("field", "type", "param1", "param2")

OBJECT_MESSAGE_KEYS = ("key", "name", "style", "order", "html", "conditions")

UPDATE_ACTION_KEYS = (
    "key",
    "name",
    "order",
    "template",
    "workflow",
    "isQuick",
    "reopenOnSave",
    "tabFocus",
    "access",
    "conditions",
    "messages",
    "isActive",
)
TAB_FOCUS_KEYS = ("left", "right")
UPDATE_ACTION_MESSAGE_KEYS = ("key", "visible")

PERIODIC_KEYS = ("key", "name", "requestType", "conditions", "actions", "cron", "schedulerName")
PERIODIC_ACTION_KEYS = ("key", "name", "typeCode", "order", "params", "conditions")

NOTIFICATION_KEYS = (
    "key",
    "name",
    "type",
    "subject",
    "format",
    "isActive",
    "sendTo",
    "extra",
    "fromEmail",
    "compressedFileName",
    "conditions",
    "attachments",
)
NOTIFICATION_SEND_TO_KEYS = (
    "requestor",
    "requestorManager",
    "owner",
    "watch",
    "role",
    "roleManager",
    "currentUser",
)
NOTIFICATION_EXTRA_KEYS = ("to", "cc", "bcc")
NOTIFICATION_ATTACHMENT_KEYS = ("field", "compressed", "sublineId")

IDS_KEYS = ("base", "explicit", "byTable")
IDS_EXPLICIT_KEYS = (
    "companyId",
    "objectTypeId",
    "objectId",
    "tabs",
    "sections",
    "fields",
    "objectDefaultLines",
    "lookups",
    "lookupValues",
    "references",
    "sources",
    "sourceValues",
    "sourceRefObjects",
    "refObjectLines",
    "workflowId",
    "workflowSteps",
    "workflowStepActions",
    "objectDefaultId",
    "objectDefaultExternalLink",
    "objectDefaultAccessOwnerLevel",
    "objectDefaultIsExternal",
    "roles",
    "statuses",
    "workflowStepAccess",
    "workflowStepNotifications",
    "updateActions",
    "objectUpdateAccess",
    "objectUpdateActionConditions",
    "objectUpdateMessages",
    "objectMessages",
    "objectMessageConditions",
    "objectActions",
    "objectActionParams",
    "objectActionConditions",
    "workflowStepObjectActions",
    "periodics",
    "periodicConditions",
    "periodicActions",
    "periodicActionParams",
    "periodicActionConditions",
    "schedulers",
    "schedulerLines",
    "schedulerLineParams",
    "notifications",
    "notificationConditions",
    "notificationAttachments",
    "subgrids",
    "subgridTabs",
    "subgridSections",
    "subgridFields",
    "subgridTemplates",
    "subgridDefaultLines",
    "subgridOnGrid",
    "objectLineOnGrid",
    "autonumbers",
    "objectServices",
    "templates",
    "objectDefaultAccess",
    "objectDefaultExternalLinks",
    "languageTables",
    "tableComments",
)
SOURCE_PROVENANCE_KEYS = ("transfer", "objectId", "objectCode", "extractedAt")

LANGUAGE_TABLE_KIND_KEYS = (
    "object",
    "company",
    "objectType",
    "workflow",
    "tabs",
    "sections",
    "templates",
    "roles",
    "statuses",
    "objectActions",
    "updateActions",
    "periodics",
    "periodicActions",
    "schedulers",
    "lines",
    "stepActions",
    "objectMessages",
    "templateHints",
    "subgrids",
)
COMMENTS_KIND_KEYS = LANGUAGE_TABLE_KIND_KEYS
COMMENT_ITEM_KEYS = ("html",)


def ordered_mapping(data: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    """Return a new dict with ``keys`` first; unknown keys keep original relative order at the end."""
    if not isinstance(data, dict):
        return data
    out: dict[str, Any] = {}
    seen: set[str] = set()
    for key in keys:
        if key in data:
            out[key] = data[key]
            seen.add(key)
    for key, value in data.items():
        if key not in seen:
            out[key] = value
    return out


def _list_maps(items: Any, fn: Callable[[dict[str, Any]], dict[str, Any]]) -> Any:
    if not isinstance(items, list):
        return items
    return [fn(item) if isinstance(item, dict) else item for item in items]


def _map_values(data: Any, fn: Callable[[dict[str, Any]], dict[str, Any]]) -> Any:
    if not isinstance(data, dict):
        return data
    return {key: fn(value) if isinstance(value, dict) else value for key, value in data.items()}


def reorder_field(field: dict[str, Any]) -> dict[str, Any]:
    field = dict(field)
    reference = field.get("reference")
    if isinstance(reference, dict):
        field["reference"] = ordered_mapping(reference, REFERENCE_BIND_KEYS)
    lookup = field.get("lookup")
    if isinstance(lookup, dict):
        field["lookup"] = _reorder_lookup_bind(lookup)
    return ordered_mapping(field, FIELD_KEYS)


def _reorder_lookup_bind(lookup: dict[str, Any]) -> dict[str, Any]:
    lookup = dict(lookup)
    values = lookup.get("values")
    if isinstance(values, list):
        lookup["values"] = _list_maps(values, lambda v: ordered_mapping(v, LOOKUP_VALUE_KEYS))
    return ordered_mapping(lookup, LOOKUP_BIND_KEYS)


def reorder_section(section: dict[str, Any]) -> dict[str, Any]:
    section = dict(section)
    section["fields"] = _list_maps(section.get("fields"), reorder_field)
    return ordered_mapping(section, SECTION_KEYS)


def reorder_tab(tab: dict[str, Any]) -> dict[str, Any]:
    tab = dict(tab)
    tab["sections"] = _list_maps(tab.get("sections"), reorder_section)
    return ordered_mapping(tab, TAB_KEYS)


def reorder_layout(layout: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(layout, dict):
        return layout
    layout = dict(layout)
    layout["tabs"] = _list_maps(layout.get("tabs"), reorder_tab)
    return ordered_mapping(layout, LAYOUT_KEYS)


def _reorder_ongrid_column(column: dict[str, Any]) -> dict[str, Any]:
    return ordered_mapping(column, ONGRID_COLUMN_KEYS)


def _reorder_ongrid_placement(placement: dict[str, Any]) -> dict[str, Any]:
    placement = dict(placement)
    placement["columns"] = _list_maps(placement.get("columns"), _reorder_ongrid_column)
    return ordered_mapping(placement, ONGRID_PLACEMENT_KEYS)


def _reorder_ongrid_layout(layout: dict[str, Any]) -> dict[str, Any]:
    layout = dict(layout)
    layout["placements"] = _list_maps(layout.get("placements"), _reorder_ongrid_placement)
    return ordered_mapping(layout, ONGRID_LAYOUT_KEYS)


def reorder_ongrid(ongrid: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(ongrid, dict):
        return ongrid
    ongrid = dict(ongrid)
    fields = ongrid.get("fields")
    if isinstance(fields, dict):
        ongrid["fields"] = _map_values(fields, lambda f: ordered_mapping(f, ONGRID_FIELD_KEYS))
    ongrid["layouts"] = _list_maps(ongrid.get("layouts"), _reorder_ongrid_layout)
    return ordered_mapping(ongrid, ONGRID_KEYS)


def _reorder_source_value(value: dict[str, Any]) -> dict[str, Any]:
    return ordered_mapping(value, SOURCE_VALUE_KEYS)


def _reorder_ref_object(ref: dict[str, Any]) -> dict[str, Any]:
    ref = dict(ref)
    lines = ref.get("lines")
    if isinstance(lines, dict):
        ref["lines"] = ordered_mapping(lines, SOURCE_REF_LINES_KEYS)
    return ordered_mapping(ref, SOURCE_REF_OBJECT_KEYS)


def reorder_reference_def(entry: dict[str, Any]) -> dict[str, Any]:
    entry = dict(entry)
    entry["values"] = _list_maps(entry.get("values"), _reorder_source_value)
    ref_object = entry.get("refObject")
    if isinstance(ref_object, dict):
        entry["refObject"] = _reorder_ref_object(ref_object)
    return ordered_mapping(entry, REFERENCE_DEF_KEYS)


def reorder_lookup_def(entry: dict[str, Any]) -> dict[str, Any]:
    entry = dict(entry)
    entry["values"] = _list_maps(entry.get("values"), lambda v: ordered_mapping(v, LOOKUP_VALUE_KEYS))
    return ordered_mapping(entry, LOOKUP_DEF_KEYS)


def _reorder_client_calc(calc: dict[str, Any]) -> dict[str, Any]:
    return ordered_mapping(calc, CLIENT_CALC_KEYS)


def _reorder_extended(extended: dict[str, Any]) -> dict[str, Any]:
    return ordered_mapping(extended, EXTENDED_KEYS)


def reorder_template_field(field: dict[str, Any]) -> dict[str, Any]:
    field = dict(field)
    extended = field.get("extended")
    if isinstance(extended, dict):
        field["extended"] = _reorder_extended(extended)
    calc = field.get("clientCalculation")
    if isinstance(calc, dict):
        field["clientCalculation"] = _reorder_client_calc(calc)
    return ordered_mapping(field, TEMPLATE_FIELD_KEYS)


def _reorder_access_line(line: dict[str, Any]) -> dict[str, Any]:
    return ordered_mapping(line, ACCESS_LINE_KEYS)


def reorder_template(template: dict[str, Any]) -> dict[str, Any]:
    template = dict(template)
    fields = template.get("fields")
    if isinstance(fields, dict):
        template["fields"] = _map_values(fields, reorder_template_field)
    template["access"] = _list_maps(template.get("access"), _reorder_access_line)
    return ordered_mapping(template, TEMPLATE_KEYS)


def reorder_subgrid_template(template: dict[str, Any]) -> dict[str, Any]:
    template = dict(template)
    fields = template.get("fields")
    if isinstance(fields, dict):
        template["fields"] = _map_values(fields, reorder_template_field)
    return ordered_mapping(template, SUBGRID_TEMPLATE_KEYS)


def reorder_subgrid(tree: dict[str, Any]) -> dict[str, Any]:
    tree = dict(tree)
    layout = tree.get("layout")
    if isinstance(layout, dict):
        tree["layout"] = reorder_layout(layout)
    tree["templates"] = _list_maps(tree.get("templates"), reorder_subgrid_template)
    ongrid = tree.get("onGrid")
    if isinstance(ongrid, dict):
        tree["onGrid"] = reorder_ongrid(ongrid)
    return ordered_mapping(tree, SUBGRID_KEYS)


def _reorder_step_action(action: dict[str, Any]) -> dict[str, Any]:
    return ordered_mapping(action, WORKFLOW_STEP_ACTION_KEYS)


def reorder_workflow_step(step: dict[str, Any]) -> dict[str, Any]:
    step = dict(step)
    step["actions"] = _list_maps(step.get("actions"), _reorder_step_action)
    step["access"] = _list_maps(step.get("access"), _reorder_access_line)
    return ordered_mapping(step, WORKFLOW_STEP_KEYS)


def reorder_workflow(workflow: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(workflow, dict):
        return workflow
    workflow = dict(workflow)
    workflow["steps"] = _list_maps(workflow.get("steps"), reorder_workflow_step)
    return ordered_mapping(workflow, WORKFLOW_KEYS)


def _reorder_condition(cond: dict[str, Any]) -> dict[str, Any]:
    return ordered_mapping(cond, ACTION_CONDITION_KEYS)


def reorder_object_action(action: dict[str, Any]) -> dict[str, Any]:
    action = dict(action)
    action["conditions"] = _list_maps(action.get("conditions"), _reorder_condition)
    return ordered_mapping(action, OBJECT_ACTION_KEYS)


def reorder_object_message(message: dict[str, Any]) -> dict[str, Any]:
    message = dict(message)
    message["conditions"] = _list_maps(message.get("conditions"), _reorder_condition)
    return ordered_mapping(message, OBJECT_MESSAGE_KEYS)


def reorder_update_action(action: dict[str, Any]) -> dict[str, Any]:
    action = dict(action)
    tab_focus = action.get("tabFocus")
    if isinstance(tab_focus, dict):
        action["tabFocus"] = ordered_mapping(tab_focus, TAB_FOCUS_KEYS)
    action["access"] = _list_maps(action.get("access"), _reorder_access_line)
    action["conditions"] = _list_maps(action.get("conditions"), _reorder_condition)
    action["messages"] = _list_maps(
        action.get("messages"), lambda m: ordered_mapping(m, UPDATE_ACTION_MESSAGE_KEYS)
    )
    return ordered_mapping(action, UPDATE_ACTION_KEYS)


def _reorder_periodic_action(action: dict[str, Any]) -> dict[str, Any]:
    action = dict(action)
    action["conditions"] = _list_maps(action.get("conditions"), _reorder_condition)
    return ordered_mapping(action, PERIODIC_ACTION_KEYS)


def reorder_periodic(periodic: dict[str, Any]) -> dict[str, Any]:
    periodic = dict(periodic)
    periodic["conditions"] = _list_maps(periodic.get("conditions"), _reorder_condition)
    periodic["actions"] = _list_maps(periodic.get("actions"), _reorder_periodic_action)
    return ordered_mapping(periodic, PERIODIC_KEYS)


def _reorder_notification_attachment(att: dict[str, Any]) -> dict[str, Any]:
    return ordered_mapping(att, NOTIFICATION_ATTACHMENT_KEYS)


def reorder_notification(item: dict[str, Any]) -> dict[str, Any]:
    item = dict(item)
    send_to = item.get("sendTo")
    if isinstance(send_to, dict):
        item["sendTo"] = ordered_mapping(send_to, NOTIFICATION_SEND_TO_KEYS)
    extra = item.get("extra")
    if isinstance(extra, dict):
        item["extra"] = ordered_mapping(extra, NOTIFICATION_EXTRA_KEYS)
    item["conditions"] = _list_maps(item.get("conditions"), _reorder_condition)
    item["attachments"] = _list_maps(item.get("attachments"), _reorder_notification_attachment)
    return ordered_mapping(item, NOTIFICATION_KEYS)


def _reorder_lang_map(entry: Any) -> Any:
    if not isinstance(entry, dict):
        return entry
    if any(not isinstance(v, str) for v in entry.values()):
        nested = dict(entry)
        html = nested.get("html")
        if isinstance(html, dict):
            nested["html"] = ordered_mapping(html, USER_LANGUAGE_CODES)
        langs = ordered_mapping(nested, USER_LANGUAGE_CODES)
        if "html" in nested:
            langs = ordered_mapping(langs, USER_LANGUAGE_CODES + ("html",))
        return langs
    return ordered_mapping(entry, USER_LANGUAGE_CODES)


def _reorder_lang_bucket(body: Any) -> Any:
    if isinstance(body, dict):
        sample = next(iter(body.values()), None)
        if isinstance(sample, dict) and sample and all(isinstance(v, dict) for v in body.values()):
            inner = next(iter(sample.values()), None)
            if isinstance(inner, dict):
                return {
                    key: _map_values(value, _reorder_lang_map) if isinstance(value, dict) else value
                    for key, value in body.items()
                }
        return _map_values(body, _reorder_lang_map)
    return body


def reorder_language_table(table: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(table, dict):
        return table
    table = {
        key: _reorder_lang_bucket(value) if key not in ("object", "company", "objectType", "workflow") else _reorder_lang_map(value)
        for key, value in table.items()
    }
    return ordered_mapping(table, LANGUAGE_TABLE_KIND_KEYS)


def _reorder_comment_item(item: Any) -> Any:
    if isinstance(item, dict):
        return ordered_mapping(item, COMMENT_ITEM_KEYS)
    return item


def _reorder_comment_bucket(body: Any) -> Any:
    if isinstance(body, list):
        return [_reorder_comment_item(item) for item in body]
    if isinstance(body, dict):
        sample = next(iter(body.values()), None)
        if isinstance(sample, list):
            return {key: _reorder_comment_bucket(value) for key, value in body.items()}
        if isinstance(sample, dict):
            inner = next(iter(sample.values()), None) if sample else None
            if isinstance(inner, list):
                return {
                    key: {ik: _reorder_comment_bucket(iv) for ik, iv in value.items()}
                    if isinstance(value, dict)
                    else value
                    for key, value in body.items()
                }
            return {key: _reorder_comment_bucket(value) for key, value in body.items()}
    return body


def reorder_comments(comments: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(comments, dict):
        return comments
    comments = {key: _reorder_comment_bucket(value) for key, value in comments.items()}
    return ordered_mapping(comments, COMMENTS_KIND_KEYS)


def reorder_ids(ids_cfg: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(ids_cfg, dict):
        return ids_cfg
    ids_cfg = dict(ids_cfg)
    explicit = ids_cfg.get("explicit")
    if isinstance(explicit, dict):
        ids_cfg["explicit"] = ordered_mapping(explicit, IDS_EXPLICIT_KEYS)
    return ordered_mapping(ids_cfg, IDS_KEYS)


def reorder_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """Walk a merged xeelo-spec and emit mappings in extract key order."""
    spec = dict(spec)
    obj = spec.get("object")
    if isinstance(obj, dict):
        obj = dict(obj)
        grid_sort = obj.get("gridSort")
        if isinstance(grid_sort, dict):
            obj["gridSort"] = ordered_mapping(grid_sort, GRID_SORT_KEYS)
        spec["object"] = ordered_mapping(obj, OBJECT_KEYS)
    ot = spec.get("objectType")
    if isinstance(ot, dict):
        spec["objectType"] = ordered_mapping(ot, OBJECT_TYPE_KEYS)
    company = spec.get("company")
    if isinstance(company, dict):
        spec["company"] = ordered_mapping(company, COMPANY_KEYS)
    layout = spec.get("layout")
    if isinstance(layout, dict):
        spec["layout"] = reorder_layout(layout)
    ongrid = spec.get("onGrid")
    if isinstance(ongrid, dict):
        spec["onGrid"] = reorder_ongrid(ongrid)
    refs = spec.get("references")
    if isinstance(refs, dict):
        spec["references"] = _map_values(refs, reorder_reference_def)
    lookups = spec.get("lookups")
    if isinstance(lookups, dict):
        spec["lookups"] = _map_values(lookups, reorder_lookup_def)
    autonumbers = spec.get("autonumbers")
    if isinstance(autonumbers, dict):
        spec["autonumbers"] = _map_values(
            autonumbers, lambda e: ordered_mapping(e, AUTONUMBER_DEF_KEYS)
        )
    object_services = spec.get("objectServices")
    if isinstance(object_services, dict):
        spec["objectServices"] = _map_values(
            object_services, lambda e: ordered_mapping(e, OBJECT_SERVICE_DEF_KEYS)
        )
    subgrids = spec.get("subgrids")
    if isinstance(subgrids, dict):
        spec["subgrids"] = _map_values(subgrids, reorder_subgrid)
    roles = spec.get("roles")
    if isinstance(roles, dict):
        spec["roles"] = _map_values(roles, lambda r: ordered_mapping(r, ROLE_KEYS))
    statuses = spec.get("statuses")
    if isinstance(statuses, dict):
        spec["statuses"] = _map_values(statuses, lambda s: ordered_mapping(s, STATUS_KEYS))
    workflow = spec.get("workflow")
    if isinstance(workflow, dict):
        spec["workflow"] = reorder_workflow(workflow)
    templates = spec.get("templates")
    if isinstance(templates, list):
        spec["templates"] = _list_maps(templates, reorder_template)
    object_default = spec.get("objectDefault")
    if isinstance(object_default, dict):
        spec["objectDefault"] = ordered_mapping(object_default, OBJECT_DEFAULT_KEYS)
    for key, fn in (
        ("objectActions", reorder_object_action),
        ("objectMessages", reorder_object_message),
        ("updateActions", reorder_update_action),
        ("periodics", reorder_periodic),
        ("notifications", reorder_notification),
    ):
        if key in spec:
            spec[key] = _list_maps(spec.get(key), fn)
    language_table = spec.get("languageTable")
    if isinstance(language_table, dict):
        spec["languageTable"] = reorder_language_table(language_table)
    comments = spec.get("comments")
    if isinstance(comments, dict):
        spec["comments"] = reorder_comments(comments)
    ids_cfg = spec.get("ids")
    if isinstance(ids_cfg, dict):
        spec["ids"] = reorder_ids(ids_cfg)
    source = spec.get("source")
    if isinstance(source, dict):
        spec["source"] = ordered_mapping(source, SOURCE_PROVENANCE_KEYS)
    return ordered_mapping(spec, SPEC_TOP_KEYS)
