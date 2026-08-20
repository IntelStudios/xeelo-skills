"""Reopen-on-save catalog (ObjectDefault / ObjectUpdateAction / WorkflowStepAction)."""

from __future__ import annotations

from typing import Any

# Omit / none / close → NULL (request closes after save). ID 0 is seed "None", not in Admin dropdown.
REOPEN_ON_SAVE_IDS: dict[str, int | None] = {
    "none": None,
    "close": None,
    "open-only-everytime": 1,
    "open-with-actions": 2,
    "open-only-assigned": 3,
}

REOPEN_ON_SAVE_NAMES: dict[int, str] = {
    1: "open-only-everytime",
    2: "open-with-actions",
    3: "open-only-assigned",
}


def reopen_on_save_id(value: Any) -> int | None:
    if value is None or value == "":
        return None
    slug = str(value).strip().lower().replace("_", "-")
    if slug not in REOPEN_ON_SAVE_IDS:
        known = ", ".join(sorted(REOPEN_ON_SAVE_IDS))
        raise ValueError(f"Unknown reopenOnSave {value!r}; expected one of: {known}")
    return REOPEN_ON_SAVE_IDS[slug]


def reopen_on_save_spec(value: Any) -> str | None:
    if value is None or value == "":
        return None
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    return REOPEN_ON_SAVE_NAMES.get(n)
