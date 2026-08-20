"""Helpers for ObjectMessage spec extract/generate."""

from __future__ import annotations

from typing import Any

from ot_builder.update_actions import condition_type_id, slugify

# Seed ObjectMessageStyle (070_SyncTables_Object.sql)
STYLE_ID_TO_SLUG: dict[int, str] = {
    1: "information",
    2: "warning",
    3: "error",
}

STYLE_SLUG_TO_ID: dict[str, int] = {
    "information": 1,
    "info": 1,
    "success": 1,
    "warning": 2,
    "error": 3,
    "danger": 3,
}

# DB column is misspelled; LanguageTable / User cache use ObjectMessageFormat.
HTML_DB_COLUMN = "ObjectMessageFromat"
HTML_LANGUAGE_COLUMN = "ObjectMessageFormat"
NAME_COLUMN = "ObjectMessageName"


def style_slug(style_id: int) -> str:
    slug = STYLE_ID_TO_SLUG.get(int(style_id))
    if not slug:
        raise ValueError(f"Unknown ObjectMessageStyleID: {style_id}")
    return slug


def style_id(value: Any) -> int:
    if value is None:
        return 1
    if isinstance(value, int):
        if value in STYLE_ID_TO_SLUG:
            return value
        raise ValueError(f"Unknown ObjectMessageStyleID: {value}")
    slug = str(value).strip().lower()
    if slug.isdigit():
        return style_id(int(slug))
    if slug not in STYLE_SLUG_TO_ID:
        raise ValueError(f"Unknown object message style: {value!r}")
    return STYLE_SLUG_TO_ID[slug]


def message_key(row: dict[str, Any], message_id: int) -> str:
    name = row.get("ObjectMessageName") if row else None
    return slugify(str(name or f"message_{message_id}"))


def condition_registry_key(msg_key: str, field_code: str, type_slug: str) -> str:
    return f"{msg_key}/{field_code}/{type_slug}"


def html_from_row(row: dict[str, Any] | None) -> str:
    if not row:
        return ""
    for col in (HTML_DB_COLUMN, HTML_LANGUAGE_COLUMN):
        val = row.get(col)
        if val is not None and str(val).strip():
            return str(val)
    return ""
