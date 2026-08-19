"""Parse Xeelo Object transfer multi-block XML into tables and hierarchy."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from ot_builder.validate import read_xml_bytes, split_xmldata_blocks

STRUCTURE_TAGS = frozenset({"ObjectSetup", "ObjectMap", "TransferInfo"})


def _row_from_element(el: ET.Element) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for child in el:
        text = child.text
        if text is None:
            continue
        if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
            row[child.tag] = int(text)
        else:
            try:
                if "." in text:
                    row[child.tag] = float(text)
                else:
                    row[child.tag] = int(text)
            except ValueError:
                row[child.tag] = text
    return row


def parse_transfer_bytes(data: bytes) -> dict[str, Any]:
    text = read_xml_bytes(data)
    blocks = split_xmldata_blocks(text)

    edges: list[dict] = []
    object_map: list[dict] = []
    transfer_info: dict[str, str] = {}
    rows: dict[str, list[dict]] = {}

    for block in blocks:
        root = ET.fromstring(block)
        for child in root:
            tag = child.tag
            if tag == "ObjectSetup":
                edges.append(_row_from_element(child))
            elif tag == "ObjectMap":
                object_map.append(_row_from_element(child))
            elif tag == "TransferInfo":
                transfer_info = _row_from_element(child)
            elif tag not in STRUCTURE_TAGS:
                rows.setdefault(tag, []).append(_row_from_element(child))

    return {
        "edges": edges,
        "objectMap": object_map,
        "transferInfo": transfer_info,
        "rows": rows,
    }


def read_transfer_bytes(path: Path) -> bytes:
    if path.suffix.lower() == ".zip":
        with ZipFile(path) as zf:
            for info in zf.infolist():
                if info.filename.endswith("/"):
                    continue
                return zf.read(info.filename)
        raise FileNotFoundError(f"No XML entry in ZIP: {path}")
    return path.read_bytes()


def materialize_zip_xml(zip_path: Path) -> Path:
    """Write the raw XML from a transfer ZIP alongside the archive."""
    zip_path = zip_path.resolve()
    with ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.filename.endswith("/"):
                continue
            data = zf.read(info.filename)
            entry_name = Path(info.filename).name
            if entry_name.lower().endswith(".xml"):
                out_path = zip_path.parent / entry_name
            else:
                out_path = zip_path.with_suffix(".xml")
            out_path.write_bytes(data)
            return out_path
    raise FileNotFoundError(f"No XML entry in ZIP: {zip_path}")


def load_transfer(path: Path) -> dict[str, Any]:
    return parse_transfer_bytes(read_transfer_bytes(path))


@dataclass
class TransferIndex:
    edges: list[dict]
    rows: dict[str, list[dict]]
    transfer_info: dict[str, str]
    children: dict[tuple[str, int], list[tuple[str, int]]] = field(default_factory=dict)
    parents: dict[tuple[str, int], list[tuple[str, int]]] = field(default_factory=dict)

    @classmethod
    def from_parsed(cls, parsed: dict[str, Any]) -> TransferIndex:
        idx = cls(
            edges=parsed["edges"],
            rows=parsed["rows"],
            transfer_info=parsed.get("transferInfo", {}),
        )
        for edge in parsed["edges"]:
            parent = (edge["TableName"], int(edge["TableRowID"]))
            child = (edge["ChildTableName"], int(edge["ChildTableRowID"]))
            idx.children.setdefault(parent, []).append(child)
            idx.parents.setdefault(child, []).append(parent)
        return idx

    def row_by_id(self, table: str, row_id: int) -> dict | None:
        id_col = f"{table}ID"
        for row in self.rows.get(table, []):
            if row.get(id_col) == row_id:
                return row
        return None

    def descendants(self, table: str, row_id: int) -> set[tuple[str, int]]:
        root = (table, row_id)
        seen: set[tuple[str, int]] = {root}
        queue = [root]
        while queue:
            current = queue.pop(0)
            for child in self.children.get(current, []):
                if child not in seen:
                    seen.add(child)
                    queue.append(child)
        return seen

    def collect_by_table(self, nodes: set[tuple[str, int]]) -> dict[str, dict[str, int]]:
        by_table: dict[str, dict[str, int]] = {}
        for table, row_id in sorted(nodes):
            by_table.setdefault(table, {})[str(row_id)] = row_id
        return by_table


def collect_table_max_ids(index: TransferIndex) -> dict[str, int]:
    """Site (or transfer) high-water PK per table. PK column is ``{Table}ID``."""
    result: dict[str, int] = {}
    for table in sorted(index.rows):
        id_col = f"{table}ID"
        max_id: int | None = None
        for row in index.rows.get(table) or []:
            raw = row.get(id_col)
            if isinstance(raw, bool):
                continue
            if isinstance(raw, int):
                parsed = raw
            elif isinstance(raw, str) and raw.isdigit():
                parsed = int(raw)
            else:
                continue
            if max_id is None or parsed > max_id:
                max_id = parsed
        if max_id is not None:
            result[table] = max_id
    return result


def find_object_row(
    parsed: dict[str, Any],
    *,
    object_id: int | None = None,
    object_code: str | None = None,
    object_name: str | None = None,
) -> dict:
    objects = parsed["rows"].get("Object", [])
    if not objects:
        raise ValueError("Transfer contains no Object rows")

    if object_id is not None:
        for obj in objects:
            if obj.get("ObjectID") == object_id:
                return obj
        raise ValueError(f"Object ID {object_id} not found")

    if object_code is not None:
        matches = [o for o in objects if o.get("ObjectCode") == object_code]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise ValueError(f"Object code {object_code!r} not found")
        raise ValueError(f"Multiple objects with code {object_code!r}")

    if object_name is not None:
        matches = [o for o in objects if o.get("ObjectName") == object_name]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise ValueError(f"Object name {object_name!r} not found")
        raise ValueError(f"Multiple objects with name {object_name!r}")

    if len(objects) == 1:
        return objects[0]
    raise ValueError("Multiple Object rows — specify --object-id, --object-code, or --object-name")
