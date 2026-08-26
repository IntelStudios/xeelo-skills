"""Extract env catalog + per-object specs from a DB transfer."""

from __future__ import annotations

import re
import shutil
from datetime import date
from pathlib import Path
from typing import Any

from ot_builder.db_parse import collect_object_by_table, load_db_transfer
from ot_builder.extract import extract_spec_from_index
from ot_builder.parse import TransferIndex, collect_table_max_ids
from ot_builder.spec_loader import write_spec

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore


def _require_yaml():
    if yaml is None:
        raise SystemExit("PyYAML is required: pip install pyyaml")
    return yaml


def _write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        _require_yaml().safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _slug(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "object"


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


def build_catalog(index: TransferIndex, *, transfer_path: Path) -> dict[str, Any]:
    companies = []
    for row in sorted(index.rows.get("Company", []), key=lambda r: int(r.get("CompanyID", 0))):
        entry: dict[str, Any] = {
            "id": int(row["CompanyID"]),
            "name": row.get("CompanyName", ""),
            "active": _boolish(row.get("IsActive", 1)),
        }
        icon = _nonempty_str(row, "CompanyTreeIcon")
        if icon:
            entry["icon"] = icon
        companies.append(entry)

    object_types = []
    for row in sorted(index.rows.get("ObjectType", []), key=lambda r: int(r.get("ObjectTypeID", 0))):
        entry: dict[str, Any] = {
            "id": int(row["ObjectTypeID"]),
            "name": row.get("ObjectTypeName", ""),
        }
        icon = _nonempty_str(row, "ObjectTypeTreeIcon")
        if icon:
            entry["icon"] = icon
        color = _nonempty_str(row, "ObjectTypeTreeColorBack")
        if color:
            entry["color"] = color
        object_types.append(entry)

    line_counts: dict[int, int] = {
        oid: len(rows) for oid, rows in index.group_by("ObjectLine", "ObjectID").items()
    }

    wf_by_object: dict[int, list[int]] = {}
    for oid, defaults in index.group_by("ObjectDefault", "ObjectID").items():
        for row in defaults:
            wfid = row.get("WorkflowID")
            if wfid is None:
                continue
            wf_by_object.setdefault(oid, [])
            wid = int(wfid)
            if wid not in wf_by_object[oid]:
                wf_by_object[oid].append(wid)

    objects = []
    for row in sorted(index.rows.get("Object", []), key=lambda r: int(r.get("ObjectID", 0))):
        oid = int(row["ObjectID"])
        objects.append(
            {
                "id": oid,
                "name": row.get("ObjectName", ""),
                "code": row.get("ObjectCode"),
                "objectTypeId": int(row.get("ObjectTypeID", 0)),
                "companyId": int(row.get("CompanyID", 0)),
                "active": _boolish(row.get("IsActive", 1)),
                "lineCount": line_counts.get(oid, 0),
                "workflowIds": wf_by_object.get(oid, []),
                "slug": _slug(row.get("ObjectName") or row.get("ObjectCode") or str(oid)),
            }
        )

    source: dict[str, Any] = {
        "transfer": str(transfer_path),
        "transferType": (index.transfer_info or {}).get("TransferType") or "DB",
        "extractedAt": date.today().isoformat(),
    }
    version = (index.transfer_info or {}).get("Version")
    if version:
        source["version"] = version
    return {
        "source": source,
        "companies": companies,
        "objectTypes": object_types,
        "objects": objects,
    }


def build_shared(index: TransferIndex) -> dict[str, Any]:
    companies = {}
    for r in index.rows.get("Company", []):
        entry: dict[str, Any] = {
            "id": int(r["CompanyID"]),
            "name": r.get("CompanyName", ""),
        }
        icon = _nonempty_str(r, "CompanyTreeIcon")
        if icon:
            entry["icon"] = icon
        companies[_slug(r.get("CompanyName") or str(r["CompanyID"]))] = entry
    object_types = {}
    for r in index.rows.get("ObjectType", []):
        entry = {
            "id": int(r["ObjectTypeID"]),
            "name": r.get("ObjectTypeName", ""),
        }
        icon = _nonempty_str(r, "ObjectTypeTreeIcon")
        if icon:
            entry["icon"] = icon
        color = _nonempty_str(r, "ObjectTypeTreeColorBack")
        if color:
            entry["color"] = color
        object_types[_slug(r.get("ObjectTypeName") or str(r["ObjectTypeID"]))] = entry
    roles = {
        _slug(r.get("RoleName") or str(r["RoleID"])): {
            "id": int(r["RoleID"]),
            "name": r.get("RoleName", ""),
            "isRequestor": _boolish(r.get("IsRequestor")),
            "isOwner": _boolish(r.get("IsOwner")),
        }
        for r in index.rows.get("Role", [])
    }
    statuses = {
        _slug(r.get("RequestStatusName") or str(r["RequestStatusID"])): {
            "id": int(r["RequestStatusID"]),
            "name": r.get("RequestStatusName", ""),
            "order": int(r.get("RequestStatusOrder", 10)) if r.get("RequestStatusOrder") is not None else 10,
            "isCompleted": _boolish(r.get("RequestStatusIsCompleted")),
            "isCanceled": _boolish(r.get("RequestStatusIsCanceled")),
        }
        for r in index.rows.get("RequestStatus", [])
    }

    sources: dict[str, Any] = {}
    values_by_source = index.group_by("ObjectLineSourceValue", "ObjectLineSourceID")
    refs_by_source = index.group_by("ObjectLineSourceRefObject", "ObjectLineSourceID")
    for row in index.rows.get("ObjectLineSource", []):
        sid = int(row["ObjectLineSourceID"])
        key = _slug(row.get("ObjectLineSourceName") or f"source-{sid}")
        base = key
        n = 1
        while key in sources:
            key = f"{base}-{n}"
            n += 1
        entry: dict[str, Any] = {
            "id": sid,
            "name": row.get("ObjectLineSourceName", ""),
            "typeId": int(row.get("ObjectLineSourceTypeID", 1)),
        }
        values = []
        for v in values_by_source.get(sid, []):
            values.append(
                {
                    "id": int(v["ObjectLineSourceValueID"]),
                    "value": v.get("ObjectLineSourceValue", ""),
                    "label": v.get("ObjectLineSourceValueName", ""),
                }
            )
        if values:
            entry["values"] = values
        refs = []
        for ref in refs_by_source.get(sid, []):
            refs.append(
                {
                    "id": int(ref["ObjectLineSourceRefObjectID"]),
                    "objectId": int(ref["ObjectID"]),
                }
            )
        if refs:
            entry["refObjects"] = refs
        sources[key] = entry

    custom_colors = []
    for row in sorted(
        index.rows.get("CustomColor", []),
        key=lambda r: int(r.get("CustomColorID", 0)),
    ):
        code = _nonempty_str(row, "CustomColorCode")
        if not code:
            continue
        color: dict[str, Any] = {
            "id": int(row["CustomColorID"]),
            "code": code,
        }
        hex_val = _nonempty_str(row, "CustomColorHEX")
        if hex_val:
            color["hex"] = hex_val
        if row.get("IsDefault") is not None:
            color["isDefault"] = _boolish(row.get("IsDefault"))
        custom_colors.append(color)

    return {
        "companies": companies,
        "objectTypes": object_types,
        "roles": roles,
        "statuses": statuses,
        "sources": sources,
        "customColors": custom_colors,
    }


def _clear_objects_dir(objects_dir: Path) -> None:
    if not objects_dir.is_dir():
        return
    for child in objects_dir.iterdir():
        if child.is_dir():
            shutil.rmtree(child)


def extract_env(
    transfer_path: Path,
    env_dir: Path,
) -> dict[str, Any]:
    parsed = load_db_transfer(transfer_path)
    index = TransferIndex.from_parsed(parsed)
    catalog = build_catalog(index, transfer_path=transfer_path)
    shared = build_shared(index)

    env_dir.mkdir(parents=True, exist_ok=True)
    _write_yaml(env_dir / "catalog.yaml", catalog)
    shared_dir = env_dir / "shared"
    _write_yaml(shared_dir / "companies.yaml", {"companies": shared["companies"]})
    _write_yaml(shared_dir / "object-types.yaml", {"objectTypes": shared["objectTypes"]})
    _write_yaml(shared_dir / "roles.yaml", {"roles": shared["roles"]})
    _write_yaml(shared_dir / "statuses.yaml", {"statuses": shared["statuses"]})
    _write_yaml(shared_dir / "sources.yaml", {"sources": shared["sources"]})
    if shared.get("customColors"):
        _write_yaml(shared_dir / "custom-colors.yaml", {"customColors": shared["customColors"]})

    objects_dir = env_dir / "objects"
    objects_dir.mkdir(parents=True, exist_ok=True)
    _clear_objects_dir(objects_dir)

    written = []
    site_base = collect_table_max_ids(index)
    for obj in catalog["objects"]:
        oid = obj["id"]
        slug = obj["slug"]
        # Disambiguate slug collisions
        out = objects_dir / slug
        if out.exists() and (out / "xeelo-spec.yaml").exists():
            out = objects_dir / f"{slug}-{oid}"
            slug = out.name

        obj_row = index.row_by_id("Object", oid)
        if not obj_row:
            raise ValueError(f"Object ID {oid} not found in transfer")
        spec = extract_spec_from_index(
            index,
            obj_row,
            source_path=transfer_path,
            include_subtree_ids=False,
            table_max_ids=site_base,
        )
        spec["ids"]["byTable"] = collect_object_by_table(index, oid)
        spec["ids"]["base"] = site_base or 9000

        write_spec(spec, out)
        written.append({"id": oid, "slug": slug, "path": str(out.relative_to(env_dir))})

    summary = {
        "catalogObjects": len(catalog["objects"]),
        "extractedObjects": written,
        "extractMode": "all",
    }
    _write_yaml(env_dir / "extract-summary.yaml", summary)
    return summary
