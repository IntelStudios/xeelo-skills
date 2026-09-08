"""ObjectLineOnGrid layout identity (size × type × module × field or sys:{code})."""

from __future__ import annotations

from typing import Any

from ot_builder.ids import IdRegistry, _as_int

DEFAULT_SIZE = "Large"
DEFAULT_TYPE = "Grid"
DEFAULT_MODULE = "Items"


def layout_id_key(size: str, grid_type: str, module: str, field_code: str) -> str:
    """Stable explicit-map key for one ObjectLineOnGrid row."""
    return f"{size}/{grid_type}/{module}/{field_code}"


def require_ongrid_id(
    registry: IdRegistry,
    *,
    size: str,
    grid_type: str,
    module: str,
    field_code: str,
    used_legacy: set[str],
) -> int:
    """Allocate or reuse an ObjectLineOnGrid ID.

    Extract keys by ``{size}/{type}/{module}/{code}``. System lines use
    ``sys:{code}`` as the last segment (see ``system_line.explicit_key_token``).
    Older specs keyed only by field code (one layout per field); that ID is
    reused for the first layout that still has no composite key.
    """
    code = str(field_code)
    composite = layout_id_key(size, grid_type, module, code)
    known = registry.get("objectLineOnGrid", composite)
    if known is not None:
        return known
    if code not in used_legacy:
        legacy = registry.get("objectLineOnGrid", code)
        if legacy is not None:
            used_legacy.add(code)
            return legacy
    return registry.require("objectLineOnGrid", composite)


def subgrid_layout_id_key(
    sub_key: str, size: str, grid_type: str, module: str, field_code: str
) -> str:
    """Stable explicit-map key for one ObjectSubLineOnGrid row."""
    return f"{sub_key}/{layout_id_key(size, grid_type, module, field_code)}"


def require_subgrid_ongrid_id(
    registry: IdRegistry,
    *,
    sub_key: str,
    size: str,
    grid_type: str,
    module: str,
    field_code: str,
    used_legacy: set[str],
) -> int:
    """Allocate or reuse an ObjectSubLineOnGrid ID.

    Extract keys by ``{sub}/{size}/{type}/{module}/{code}``. Older specs keyed
    ``{sub}/{code}``; that ID is reused for the first layout that still has no
    composite key.
    """
    code = str(field_code)
    composite = subgrid_layout_id_key(sub_key, size, grid_type, module, code)
    known = registry.get("subgridOnGrid", composite)
    if known is not None:
        return known
    legacy_key = f"{sub_key}/{code}"
    if legacy_key not in used_legacy:
        legacy = registry.get("subgridOnGrid", legacy_key)
        if legacy is not None:
            used_legacy.add(legacy_key)
            return legacy
    return registry.require("subgridOnGrid", composite)


def column_token(col: dict[str, Any]) -> str:
    """Stable label for one placement column (field xor systemLine)."""
    field_code = col.get("field")
    sys_code = col.get("systemLine")
    if field_code and sys_code:
        return f"{field_code}/{sys_code}"
    if sys_code:
        return f"sys:{sys_code}"
    return str(field_code or "?")


def validate_layout_placements(
    placements: list[Any],
    *,
    context: str,
) -> None:
    """Reject duplicate field/systemLine in one layout and overlapping cells.

    Interval is half-open: ``position`` + ``length`` occupies
    ``[position, position + length)``. The next column on the same row must
    start at ``position + length`` or later.
    """
    seen: dict[str, str] = {}
    for placement in placements:
        if not isinstance(placement, dict):
            continue
        row_letter = str(placement.get("row") or "T")
        columns = placement.get("columns") or []
        intervals: list[tuple[int, int, str]] = []
        for col in columns:
            if not isinstance(col, dict):
                continue
            token = column_token(col)
            if token in seen:
                raise ValueError(
                    f"{context}: {token} already placed on row {seen[token]} "
                    "(one onGrid row per size/type/module/field)"
                )
            seen[token] = row_letter
            pos = _as_int(col.get("position"))
            length = _as_int(col.get("length"))
            if pos is None:
                pos = 1
            if length is None:
                length = 100
            intervals.append((pos, pos + length, token))
        intervals.sort(key=lambda item: (item[0], item[1], item[2]))
        for prev, cur in zip(intervals, intervals[1:]):
            prev_start, prev_end, prev_token = prev
            start, _end, token = cur
            if start < prev_end:
                raise ValueError(
                    f"{context} row {row_letter}: {token} at position {start} "
                    f"overlaps {prev_token} occupying {prev_start}–{prev_end} "
                    "(half-open; next position must be >= previous position + length)"
                )


def deactivate_unused_ongrid_rows(
    registry: IdRegistry,
    category: str,
    used_ids: set[int],
    *,
    id_column: str,
    extra: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Emit leftover explicit Orig. IDs with IsActive=0 so OT upload deletes them.

    Object Transfer insert for ObjectLineOnGrid / ObjectSubLineOnGrid keeps
    ``IsActive = 1`` only. Rows in JSON with ``IsActive = 0`` match for delete
    and are not re-inserted. Omitting a dropped placement leaves the live row
    and it can overlap the new layout.
    """
    extra = extra or {}
    rows: list[dict[str, Any]] = []
    seen: set[int] = set()
    for og_id in registry.explicit_values(category):
        if og_id in used_ids or og_id in seen:
            continue
        seen.add(og_id)
        row: dict[str, Any] = {id_column: og_id, "IsActive": 0}
        row.update(extra)
        rows.append(row)
    return rows
