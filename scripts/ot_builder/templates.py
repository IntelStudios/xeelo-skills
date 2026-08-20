"""ObjectDefault templates and extended-validation helpers."""

from __future__ import annotations

import re
import uuid
from typing import Any

from ot_builder.ids import IdRegistry
from ot_builder.spec_loader import spec_references
from ot_builder.update_actions import slugify

VALIDATION_MANDATORY = 1
VALIDATION_OPTIONAL = 2
VALIDATION_EXTENDED = 9

ID_FIELD_RE = re.compile(r"id\{([A-Za-z0-9_]+)\}")
SOURCE_VALUE_RE = re.compile(r"\{([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)\}")

REFERENCE_FIELD_TYPES = frozenset(
    {
        "combobox",
        "combobox_search",
        "combobox_server",
        "radio",
        "checkbox_multiselect",
    }
)
COMBO_FIELD_TYPES = frozenset({"combobox", "combobox_search", "combobox_server"})
LOOKUP_FIELD_TYPES = frozenset(
    {
        "combobox",
        "combobox_search",
        "text",
        "checkbox",
        "date",
        "number",
        "combobox_server",
        "time",
        "radio",
        "checkbox_multiselect",
    }
)

CLIENT_CALC_TYPE_IDS = {
    "math": 1,
    "string": 2,
    "service": 3,
    "date_add": 4,
    "date_diff": 5,
    "focus": 6,
    "user_info": 7,
    "device_info": 8,
}
CLIENT_CALC_ID_TYPES = {value: key for key, value in CLIENT_CALC_TYPE_IDS.items()}
PLACEHOLDER_CALC_TYPES = frozenset({"user_info", "device_info"})
PLACEHOLDER_PARAM_RE = re.compile(r"^\{[^{}]+\}")


def lookup_source_bind(spec: dict, source_key: str, value_key: str) -> str:
    references = spec_references(spec)
    if source_key not in references:
        raise ValueError(f"Unknown reference key in extended validation: {source_key!r}")
    for value_def in references[source_key].get("values") or []:
        val = str(value_def["value"])
        bind = str(value_def.get("bind", value_def["value"]))
        if value_key in (val, bind):
            return bind
    raise ValueError(f"Unknown source value {source_key}.{value_key}")


def format_bind_for_grammar(bind: str) -> str:
    """Emit a Xeelo Grammar literal for ObjectLineSourceValueBind.

    Numeric binds stay unquoted (mathCondition INT). Everything else is a
    G4 STRING: single quotes, with ``\\`` and ``'`` escaped.
    """
    if re.fullmatch(r"-?\d+", bind):
        return bind
    escaped = bind.replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


def compile_extended_condition(expr: str, spec: dict, registry: IdRegistry) -> str:
    def repl_id(match: re.Match[str]) -> str:
        code = match.group(1)
        line_id = registry.require("fields", code)
        return f"id{line_id}"

    compiled = ID_FIELD_RE.sub(repl_id, expr)

    def repl_src(match: re.Match[str]) -> str:
        source_key, value_key = match.group(1), match.group(2)
        bind = lookup_source_bind(spec, source_key, value_key)
        return format_bind_for_grammar(bind)

    return SOURCE_VALUE_RE.sub(repl_src, compiled)


def decompile_extended_condition(
    expr: str,
    field_id_to_code: dict[int, str],
    sources_spec: dict[str, dict],
) -> str:
    result = expr
    for line_id, code in sorted(field_id_to_code.items(), key=lambda item: -len(str(item[0]))):
        result = result.replace(f"id{line_id}", f"id{{{code}}}")

    replacements: list[tuple[str, str]] = []
    for source_key, source_def in sources_spec.items():
        for value_def in source_def.get("values") or []:
            value_key = str(value_def["value"])
            bind = str(value_def.get("bind", value_def["value"]))
            replacements.append((bind, f"{{{source_key}.{value_key}}}"))
    replacements.sort(key=lambda item: -len(item[0]))
    for bind, placeholder in replacements:
        if not bind:
            continue
        grammar_form = format_bind_for_grammar(bind)
        if grammar_form != bind:
            result = result.replace(grammar_form, placeholder)
            result = result.replace(f'"{bind}"', placeholder)
        result = re.sub(
            rf"(?<![A-Za-z0-9_{{']){re.escape(bind)}(?![A-Za-z0-9_}}'])",
            placeholder,
            result,
        )
    return result


def iter_layout_fields(spec: dict) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    for tab in (spec.get("layout") or {}).get("tabs") or []:
        for section in tab.get("sections") or []:
            for field in section.get("fields") or []:
                fields.append(field)
    return fields


def iter_templates(spec: dict) -> list[dict[str, Any]]:
    templates = spec.get("templates")
    if templates:
        return list(templates)
    cfg = dict(spec.get("objectDefault") or {})
    cfg.setdefault("key", "default")
    cfg.setdefault("name", cfg.get("name", "Default"))
    cfg.setdefault("isDefault", True)
    cfg.setdefault("order", 0)
    return [cfg]


def is_legacy_single_template(spec: dict) -> bool:
    templates = spec.get("templates") or []
    return len(templates) <= 1


def template_line_key(template_key: str, field_code: str, *, legacy: bool) -> str:
    if legacy:
        return field_code
    return f"{template_key}/{field_code}"


def template_access_registry_key(
    template_key: str,
    field_code: str,
    subline_id: int | None = None,
    *,
    legacy: bool,
) -> str:
    base = template_line_key(template_key, field_code, legacy=legacy)
    if subline_id is not None:
        return f"{base}/sub{subline_id}"
    return base


def resolve_template_id(registry: IdRegistry, key: str, *, is_default: bool) -> int:
    mapped = registry.optional("templates", key)
    if mapped is not None:
        return mapped
    if is_default:
        tid = registry.require_scalar("objectDefaultId")
        registry._allocated.setdefault("templates", {})[key] = tid  # noqa: SLF001
        return tid
    return registry.require("templates", key)


def apply_template_line_validation(
    template_line: dict[str, Any],
    *,
    field: dict[str, Any],
    template_field: dict[str, Any] | None,
    spec: dict,
    registry: IdRegistry,
) -> None:
    cfg = dict(template_field or {})
    hidden = cfg.get("hidden")
    extended = dict(cfg.get("extended") or {})
    mandatory = cfg.get("mandatory", field.get("mandatory"))

    if hidden is True:
        extended.setdefault("hidden", "true")

    if extended:
        template_line["ObjectDefaultLineValidationID"] = VALIDATION_EXTENDED
        for spec_key, column in (
            ("hidden", "ObjectDefaultLineValidationExtHiddenCondition"),
            ("disabled", "ObjectDefaultLineValidationExtDisabledCondition"),
            ("mandatory", "ObjectDefaultLineValidationExtMandatoryCondition"),
        ):
            raw = extended.get(spec_key)
            if raw is None:
                continue
            template_line[column] = compile_extended_condition(str(raw), spec, registry)
        return

    if mandatory:
        template_line["ObjectDefaultLineValidationID"] = VALIDATION_MANDATORY
        return

    template_line["ObjectDefaultLineValidationID"] = VALIDATION_OPTIONAL


def apply_template_line_extras(
    template_line: dict[str, Any],
    *,
    field: dict[str, Any],
    template_field: dict[str, Any] | None,
    spec: dict,
    registry: IdRegistry,
) -> None:
    cfg = dict(template_field or {})
    if cfg.get("alwaysDisabled"):
        template_line["ObjectDefaultLineIsDisabled"] = 1
    if cfg.get("defaultValue") is not None:
        value = str(cfg["defaultValue"])
        if field.get("type") == "description_memo":
            template_line["ObjectDefaultLineDescMemo"] = value
        else:
            template_line["ObjectDefaultLineValue"] = value

    calc = cfg.get("clientCalculation")
    if not isinstance(calc, dict) or not calc.get("type"):
        return
    type_slug = str(calc["type"])
    if type_slug not in CLIENT_CALC_TYPE_IDS:
        raise ValueError(f"Unknown clientCalculation.type {type_slug!r}")
    template_line["ObjectDefaultLineClientCalculationTypeID"] = CLIENT_CALC_TYPE_IDS[type_slug]
    expr = calc.get("expr")
    if type_slug in PLACEHOLDER_CALC_TYPES:
        expr_str = "" if expr is None else str(expr).strip()
        if not PLACEHOLDER_PARAM_RE.fullmatch(expr_str):
            raise ValueError(
                f"clientCalculation.type {type_slug!r} requires expr as a single {{Placeholder}}"
            )
        expr = expr_str
    if expr is not None and str(expr) != "":
        template_line["ObjectDefaultLineClientCalculation"] = compile_extended_condition(
            str(expr), spec, registry
        )


def template_field_spec_from_line(
    row: dict[str, Any],
    field_id_to_code: dict[int, str],
    sources_spec: dict[str, dict],
    autonumber_id_to_key: dict[int, str] | None = None,
) -> dict[str, Any] | None:
    validation_id = row.get("ObjectDefaultLineValidationID")
    hidden_cond = row.get("ObjectDefaultLineValidationExtHiddenCondition")
    disabled_cond = row.get("ObjectDefaultLineValidationExtDisabledCondition")
    mandatory_cond = row.get("ObjectDefaultLineValidationExtMandatoryCondition")
    spec_field: dict[str, Any] = {}

    if str(row.get("ObjectDefaultLineIsDisabled")) in ("1", "True", "true"):
        spec_field["alwaysDisabled"] = True

    if validation_id is not None and int(validation_id) == VALIDATION_MANDATORY:
        spec_field["mandatory"] = True

    if validation_id is not None and int(validation_id) == VALIDATION_EXTENDED:
        if str(hidden_cond).strip().lower() == "true" and not disabled_cond and not mandatory_cond:
            spec_field["hidden"] = True
        else:
            extended: dict[str, str] = {}
            if hidden_cond:
                if str(hidden_cond).strip().lower() == "true":
                    spec_field["hidden"] = True
                else:
                    extended["hidden"] = decompile_extended_condition(
                        str(hidden_cond), field_id_to_code, sources_spec
                    )
            if disabled_cond:
                extended["disabled"] = decompile_extended_condition(
                    str(disabled_cond), field_id_to_code, sources_spec
                )
            if mandatory_cond:
                extended["mandatory"] = decompile_extended_condition(
                    str(mandatory_cond), field_id_to_code, sources_spec
                )
            if extended:
                spec_field["extended"] = extended

    desc_html = row.get("ObjectDefaultLineDescMemo")
    if desc_html is not None and str(desc_html) != "":
        spec_field["defaultValue"] = str(desc_html)
    else:
        default_value = row.get("ObjectDefaultLineValue")
        if default_value is not None and str(default_value) != "":
            spec_field["defaultValue"] = str(default_value)

    calc_type_id = row.get("ObjectDefaultLineClientCalculationTypeID")
    calc_expr = row.get("ObjectDefaultLineClientCalculation")
    if calc_type_id is not None:
        type_slug = CLIENT_CALC_ID_TYPES.get(int(calc_type_id))
        if type_slug:
            calc_spec: dict[str, Any] = {"type": type_slug}
            if calc_expr:
                calc_spec["expr"] = decompile_extended_condition(
                    str(calc_expr), field_id_to_code, sources_spec
                )
            spec_field["clientCalculation"] = calc_spec

    autonumber_id = row.get("ObjectDefaultLineAutoNumberID")
    if autonumber_id is not None and autonumber_id_to_key:
        key = autonumber_id_to_key.get(int(autonumber_id))
        if key:
            spec_field["autonumber"] = key

    return spec_field or None


def new_external_link() -> str:
    return str(uuid.uuid4()).upper()


def template_slug_from_name(name: str, template_id: int) -> str:
    return slugify(name) or f"template_{template_id}"
