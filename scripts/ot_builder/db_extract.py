"""Extract env catalog + per-object specs from a DB transfer."""

from __future__ import annotations

import re
import shutil
from datetime import date
from pathlib import Path
from typing import Any

from ot_builder.db_parse import collect_object_by_table, load_db_transfer
from ot_builder.extract import extract_spec
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


def build_catalog(index: TransferIndex, *, transfer_path: Path) -> dict[str, Any]:
    companies = []
    for row in sorted(index.rows.get("Company", []), key=lambda r: int(r.get("CompanyID", 0))):
        companies.append(
            {
                "id": int(row["CompanyID"]),
                "name": row.get("CompanyName", ""),
                "active": _boolish(row.get("IsActive", 1)),
            }
        )

    object_types = []
    for row in sorted(index.rows.get("ObjectType", []), key=lambda r: int(r.get("ObjectTypeID", 0))):
        object_types.append(
            {
                "id": int(row["ObjectTypeID"]),
                "name": row.get("ObjectTypeName", ""),
            }
        )

    line_counts: dict[int, int] = {}
    for row in index.rows.get("ObjectLine", []):
        oid = int(row.get("ObjectID", 0))
        line_counts[oid] = line_counts.get(oid, 0) + 1

    wf_by_object: dict[int, list[int]] = {}
    for row in index.rows.get("ObjectDefault", []):
        oid = int(row.get("ObjectID", 0))
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

    return {
        "source": {
            "transfer": str(transfer_path),
            "transferType": (index.transfer_info or {}).get("TransferType", "DB"),
            "version": (index.transfer_info or {}).get("Version"),
            "extractedAt": date.today().isoformat(),
        },
        "companies": companies,
        "objectTypes": object_types,
        "objects": objects,
    }


def build_shared(index: TransferIndex) -> dict[str, Any]:
    companies = {
        _slug(r.get("CompanyName") or str(r["CompanyID"])): {
            "id": int(r["CompanyID"]),
            "name": r.get("CompanyName", ""),
        }
        for r in index.rows.get("Company", [])
    }
    object_types = {
        _slug(r.get("ObjectTypeName") or str(r["ObjectTypeID"])): {
            "id": int(r["ObjectTypeID"]),
            "name": r.get("ObjectTypeName", ""),
        }
        for r in index.rows.get("ObjectType", [])
    }
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
        for v in index.rows.get("ObjectLineSourceValue", []):
            if int(v.get("ObjectLineSourceID", 0)) != sid:
                continue
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
        for ref in index.rows.get("ObjectLineSourceRefObject", []):
            if int(ref.get("ObjectLineSourceID", 0)) != sid:
                continue
            refs.append(
                {
                    "id": int(ref["ObjectLineSourceRefObjectID"]),
                    "objectId": int(ref["ObjectID"]),
                }
            )
        if refs:
            entry["refObjects"] = refs
        sources[key] = entry

    return {
        "companies": companies,
        "objectTypes": object_types,
        "roles": roles,
        "statuses": statuses,
        "sources": sources,
    }


def extract_subgrids(index: TransferIndex, object_id: int) -> dict[str, Any] | None:
    sub_ids: set[int] = set()
    for row in index.rows.get("ObjectLine", []):
        if int(row.get("ObjectID", 0)) != object_id:
            continue
        if row.get("ObjectSubID") is not None:
            sub_ids.add(int(row["ObjectSubID"]))
    if not sub_ids:
        return None

    subgrids: dict[str, Any] = {}
    for sub_id in sorted(sub_ids):
        sub = index.row_by_id("ObjectSub", sub_id)
        if not sub:
            continue
        key = _slug(sub.get("ObjectSubName") or sub.get("ObjectSubCode") or str(sub_id))
        lines = []
        for line in sorted(
            [r for r in index.rows.get("ObjectSubLine", []) if int(r.get("ObjectSubID", 0)) == sub_id],
            key=lambda r: (r.get("ObjectSubLineOrder") or 0, r.get("ObjectSubLineID") or 0),
        ):
            lines.append(
                {
                    "id": int(line["ObjectSubLineID"]),
                    "name": line.get("ObjectSubLineName", ""),
                    "code": line.get("ObjectSubLineCode"),
                    "slot": line.get("ObjectSubLineSlot"),
                    "order": line.get("ObjectSubLineOrder"),
                    "typeId": line.get("ObjectSubLineTypeID"),
                }
            )
        subgrids[key] = {
            "id": sub_id,
            "name": sub.get("ObjectSubName", ""),
            "code": sub.get("ObjectSubCode"),
            "width": sub.get("ObjectSubWidth"),
            "lines": lines,
        }
    return subgrids or None


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

        spec = extract_spec(transfer_path, object_id=oid)
        spec["ids"]["byTable"] = collect_object_by_table(index, oid)
        spec["ids"]["base"] = site_base or 9000

        subgrids = extract_subgrids(index, oid)
        if subgrids:
            spec["subgrids"] = subgrids

        write_spec(spec, out)
        written.append({"id": oid, "slug": slug, "path": str(out.relative_to(env_dir))})

    summary = {
        "catalogObjects": len(catalog["objects"]),
        "extractedObjects": written,
        "extractMode": "all",
    }
    _write_yaml(env_dir / "extract-summary.yaml", summary)
    return summary
