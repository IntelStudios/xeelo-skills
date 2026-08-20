"""ObjectLineOnGrid layout identity (size × type × module × field)."""

from __future__ import annotations

from ot_builder.ids import IdRegistry

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

    Extract keys by ``{size}/{type}/{module}/{code}``. Older specs keyed only
    by field code (one layout per field); that ID is reused for the first
    layout that still has no composite key.
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
