"""Load and write multi-file xeelo-spec.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

ENTRY_FILENAME = "xeelo-spec.yaml"
METADATA_KEYS = ("version", "kind", "transferType", "transferVersion", "includes")
OBJECT_FRAGMENT_KEYS = ("object", "company", "layout", "onGrid", "sources")
WORKFLOW_FRAGMENT_KEYS = ("roles", "statuses", "workflow")
TEMPLATE_FRAGMENT_KEYS = ("templates", "objectDefault")
OBJECT_ACTION_FRAGMENT_KEYS = ("objectActions",)
UPDATE_ACTION_FRAGMENT_KEYS = ("updateActions",)
SUBGRIDS_FRAGMENT_KEYS = ("subgrids",)
IDS_FRAGMENT_KEYS = ("ids", "source")


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


def _merge_specs(base: dict, overlay: dict) -> dict:
    merged = dict(base)
    for key, value in overlay.items():
        if key == "includes":
            continue
        merged[key] = value
    return merged


def load_spec(path: Path) -> dict:
    """Load monolithic spec or entry file with includes."""
    entry = _resolve_entry(path)
    spec = _read_yaml(entry)

    includes = spec.get("includes")
    if not includes:
        spec.pop("includes", None)
        return spec

    if not isinstance(includes, list):
        raise ValueError(f"'includes' must be a list in {entry}")

    merged = {key: spec[key] for key in METADATA_KEYS if key in spec and key != "includes"}
    for rel in includes:
        fragment_path = (entry.parent / rel).resolve()
        if not fragment_path.is_file():
            raise FileNotFoundError(f"Include not found: {fragment_path} (from {entry})")
        merged = _merge_specs(merged, _read_yaml(fragment_path))

    return merged


def write_spec(spec: dict, directory: Path) -> Path:
    """Write split spec files into directory; returns entry path."""
    directory.mkdir(parents=True, exist_ok=True)
    spec_dir = directory / "spec"
    spec_dir.mkdir(parents=True, exist_ok=True)

    includes: list[str] = []

    object_fragment = {key: spec[key] for key in OBJECT_FRAGMENT_KEYS if key in spec}
    if object_fragment:
        object_path = spec_dir / "object.yaml"
        _write_yaml(object_path, object_fragment)
        includes.append(f"spec/{object_path.name}")

    workflow_fragment = {key: spec[key] for key in WORKFLOW_FRAGMENT_KEYS if key in spec}
    if workflow_fragment:
        workflow_path = spec_dir / "workflow.yaml"
        _write_yaml(workflow_path, workflow_fragment)
        includes.append(f"spec/{workflow_path.name}")

    template_fragment = {key: spec[key] for key in TEMPLATE_FRAGMENT_KEYS if key in spec}
    if template_fragment:
        template_path = spec_dir / "templates.yaml"
        _write_yaml(template_path, template_fragment)
        includes.append(f"spec/{template_path.name}")

    object_action_fragment = {key: spec[key] for key in OBJECT_ACTION_FRAGMENT_KEYS if key in spec}
    if object_action_fragment:
        object_action_path = spec_dir / "object-actions.yaml"
        _write_yaml(object_action_path, object_action_fragment)
        includes.append(f"spec/{object_action_path.name}")

    update_fragment = {key: spec[key] for key in UPDATE_ACTION_FRAGMENT_KEYS if key in spec}
    if update_fragment:
        update_path = spec_dir / "update-actions.yaml"
        _write_yaml(update_path, update_fragment)
        includes.append(f"spec/{update_path.name}")

    subgrids_fragment = {key: spec[key] for key in SUBGRIDS_FRAGMENT_KEYS if key in spec}
    if subgrids_fragment:
        subgrids_path = spec_dir / "subgrids.yaml"
        _write_yaml(subgrids_path, subgrids_fragment)
        includes.append(f"spec/{subgrids_path.name}")

    ids_fragment = {key: spec[key] for key in IDS_FRAGMENT_KEYS if key in spec}
    if ids_fragment:
        ids_path = spec_dir / "ids.yaml"
        _write_yaml(ids_path, ids_fragment)
        includes.append(f"spec/{ids_path.name}")

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
