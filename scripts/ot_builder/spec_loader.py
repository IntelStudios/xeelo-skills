"""Load and write multi-file xeelo-spec.yaml."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

ENTRY_FILENAME = "xeelo-spec.yaml"
METADATA_KEYS = ("version", "kind", "transferType", "transferVersion", "includes")
OBJECT_FRAGMENT_KEYS = ("object", "objectType", "company", "layout", "onGrid")
REFERENCES_FRAGMENT_KEYS = ("references",)
LOOKUPS_FRAGMENT_KEYS = ("lookups",)
AUTONUMBERS_FRAGMENT_KEYS = ("autonumbers",)
LANGUAGE_TABLE_FRAGMENT_KEYS = ("languageTable",)
COMMENTS_FRAGMENT_KEYS = ("comments",)
WORKFLOW_FRAGMENT_KEYS = ("roles", "statuses", "workflow")
TEMPLATE_FRAGMENT_KEYS = ("templates", "objectDefault")
OBJECT_ACTION_FRAGMENT_KEYS = ("objectActions",)
UPDATE_ACTION_FRAGMENT_KEYS = ("updateActions",)
OBJECT_MESSAGE_FRAGMENT_KEYS = ("objectMessages",)
PERIODICS_FRAGMENT_KEYS = ("periodics",)
NOTIFICATIONS_FRAGMENT_KEYS = ("notifications",)
SUBGRIDS_FRAGMENT_KEYS = ("subgrids",)
IDS_FRAGMENT_KEYS = ("ids", "source")
MAP_MERGE_KEYS = frozenset({"references", "lookups", "autonumbers"})


def _require_yaml() -> Any:
    if yaml is None:
        raise SystemExit("PyYAML is required: pip install pyyaml")
    return yaml


def _read_yaml(path: Path) -> dict:
    data = _require_yaml().safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping in {path}")
    return data


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        _require_yaml().safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _resolve_entry(path: Path) -> Path:
    if path.is_dir():
        entry = path / ENTRY_FILENAME
        if not entry.is_file():
            raise FileNotFoundError(f"Missing {ENTRY_FILENAME} in {path}")
        return entry
    return path


def spec_references(spec: dict) -> dict[str, Any]:
    """Named ObjectLineSource definitions (`references:`, alias `sources:`)."""
    refs = dict(spec.get("references") or {})
    for key, value in (spec.get("sources") or {}).items():
        refs.setdefault(key, value)
    return refs


def _normalize_reference_binding(ref: dict) -> dict:
    out = dict(ref)
    if "reference" not in out and out.get("source"):
        out["reference"] = out.pop("source")
    else:
        out.pop("source", None)
    if "referenceId" not in out and out.get("sourceId") is not None:
        out["referenceId"] = out.pop("sourceId")
    else:
        out.pop("sourceId", None)
    return out


def _walk_layout_fields(spec: dict):
    for tab in (spec.get("layout") or {}).get("tabs") or []:
        for section in tab.get("sections") or []:
            for field in section.get("fields") or []:
                yield field


def normalize_spec(spec: dict) -> dict:
    """Canonical spec: `references` (not `sources`), `reference.reference` / `referenceId`."""
    spec = copy.deepcopy(spec)
    refs = spec_references(spec)
    if refs:
        spec["references"] = refs
    spec.pop("sources", None)

    ids_cfg = spec.get("ids")
    if isinstance(ids_cfg, dict):
        ids_cfg = dict(ids_cfg)
        explicit = ids_cfg.get("explicit")
        if isinstance(explicit, dict):
            explicit = dict(explicit)
            if "sources" in explicit:
                ref_ids = dict(explicit.get("references") or {})
                for key, value in (explicit.get("sources") or {}).items():
                    ref_ids.setdefault(key, value)
                explicit["references"] = ref_ids
                del explicit["sources"]
            ids_cfg["explicit"] = explicit
        spec["ids"] = ids_cfg

    for field in _walk_layout_fields(spec):
        reference = field.get("reference")
        if isinstance(reference, dict):
            field["reference"] = _normalize_reference_binding(reference)
    return spec


def _fold_sources_into_references(data: dict) -> dict:
    overlay = dict(data)
    if "sources" in overlay:
        refs = dict(overlay.get("references") or {})
        for key, value in (overlay.get("sources") or {}).items():
            refs.setdefault(key, value)
        overlay["references"] = refs
        del overlay["sources"]
    return overlay


def _merge_specs(base: dict, overlay: dict) -> dict:
    merged = dict(base)
    overlay = _fold_sources_into_references(overlay)
    for key, value in overlay.items():
        if key == "includes":
            continue
        if key in MAP_MERGE_KEYS and isinstance(value, dict):
            merged[key] = {**(merged.get(key) or {}), **value}
        else:
            merged[key] = value
    return merged


def load_spec(path: Path) -> dict:
    """Load monolithic spec or entry file with includes."""
    entry = _resolve_entry(path)
    spec = _read_yaml(entry)

    includes = spec.get("includes")
    if not includes:
        spec.pop("includes", None)
        return normalize_spec(spec)

    if not isinstance(includes, list):
        raise ValueError(f"'includes' must be a list in {entry}")

    merged = {key: spec[key] for key in METADATA_KEYS if key in spec and key != "includes"}
    for rel in includes:
        fragment_path = (entry.parent / rel).resolve()
        if not fragment_path.is_file():
            raise FileNotFoundError(f"Include not found: {fragment_path} (from {entry})")
        merged = _merge_specs(merged, _read_yaml(fragment_path))

    return normalize_spec(merged)


def _write_fragment(
    spec_dir: Path,
    includes: list[str],
    spec: dict,
    keys: tuple[str, ...],
    filename: str,
) -> None:
    fragment = {key: spec[key] for key in keys if key in spec}
    if not fragment:
        return
    path = spec_dir / filename
    _write_yaml(path, fragment)
    includes.append(f"spec/{path.name}")


def write_spec(spec: dict, directory: Path) -> Path:
    """Write split spec files into directory; returns entry path."""
    spec = normalize_spec(spec)
    directory.mkdir(parents=True, exist_ok=True)
    spec_dir = directory / "spec"
    spec_dir.mkdir(parents=True, exist_ok=True)

    includes: list[str] = []
    _write_fragment(spec_dir, includes, spec, OBJECT_FRAGMENT_KEYS, "object.yaml")
    _write_fragment(spec_dir, includes, spec, REFERENCES_FRAGMENT_KEYS, "references.yaml")
    _write_fragment(spec_dir, includes, spec, LOOKUPS_FRAGMENT_KEYS, "lookups.yaml")
    _write_fragment(spec_dir, includes, spec, AUTONUMBERS_FRAGMENT_KEYS, "autonumbers.yaml")
    _write_fragment(spec_dir, includes, spec, LANGUAGE_TABLE_FRAGMENT_KEYS, "language-table.yaml")
    _write_fragment(spec_dir, includes, spec, COMMENTS_FRAGMENT_KEYS, "comments.yaml")
    _write_fragment(spec_dir, includes, spec, WORKFLOW_FRAGMENT_KEYS, "workflow.yaml")
    _write_fragment(spec_dir, includes, spec, TEMPLATE_FRAGMENT_KEYS, "templates.yaml")
    _write_fragment(spec_dir, includes, spec, OBJECT_ACTION_FRAGMENT_KEYS, "object-actions.yaml")
    _write_fragment(spec_dir, includes, spec, OBJECT_MESSAGE_FRAGMENT_KEYS, "object-messages.yaml")
    _write_fragment(spec_dir, includes, spec, UPDATE_ACTION_FRAGMENT_KEYS, "update-actions.yaml")
    _write_fragment(spec_dir, includes, spec, PERIODICS_FRAGMENT_KEYS, "periodics.yaml")
    _write_fragment(spec_dir, includes, spec, NOTIFICATIONS_FRAGMENT_KEYS, "notifications.yaml")
    _write_fragment(spec_dir, includes, spec, SUBGRIDS_FRAGMENT_KEYS, "subgrids.yaml")
    _write_fragment(spec_dir, includes, spec, IDS_FRAGMENT_KEYS, "ids.yaml")

    entry: dict[str, Any] = {}
    for key in METADATA_KEYS:
        if key == "includes":
            continue
        if key in spec:
            entry[key] = spec[key]
    entry["includes"] = includes

    entry_path = directory / ENTRY_FILENAME
    _write_yaml(entry_path, entry)
    return entry_path
