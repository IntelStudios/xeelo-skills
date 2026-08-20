"""Parse Xeelo Object/DB transfer multi-block XML into tables and hierarchy."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from html import unescape
from pathlib import Path
from typing import Any, Iterable
from zipfile import ZipFile

from ot_builder.validate import ValidationError, iter_xmldata_blocks, read_xml_bytes

STRUCTURE_TAGS = frozenset({"ObjectSetup", "ObjectMap", "TransferInfo"})

_XMLDATA_OPEN = "<XMLData>"
_XMLDATA_CLOSE = "</XMLData>"


def _pk_int(val: Any) -> int | None:
    if val is None or isinstance(val, bool):
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, float) and val.is_integer():
        return int(val)
    if isinstance(val, str):
        text = val.strip()
        if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
            return int(text)
    return None


def _group_key_part(val: Any) -> Any:
    parsed = _pk_int(val)
    return parsed if parsed is not None else val


def coerce_xml_text(text: str) -> Any:
    """Match ElementTree row coercion: int, float, or string."""
    if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
        return int(text)
    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        return text


def _is_tag_boundary(ch: str) -> bool:
    return ch in ">/ \t\n\r"


def _find_matching_close(inner: str, tag: str, body_start: int) -> int | None:
    """Return start index of ``</tag>`` matching the open at the same nesting depth."""
    open_prefix = f"<{tag}"
    close = f"</{tag}>"
    depth = 1
    search = body_start
    length = len(inner)
    while search < length:
        next_open = inner.find(open_prefix, search)
        next_close = inner.find(close, search)
        if next_close == -1:
            return None
        if next_open != -1 and next_open < next_close:
            after = next_open + len(open_prefix)
            if after < length and _is_tag_boundary(inner[after]):
                depth += 1
                search = after
                continue
            search = after
            continue
        depth -= 1
        if depth == 0:
            return next_close
        search = next_close + len(close)
    return None


def _iter_child_elements(inner: str) -> Iterable[tuple[str, str]]:
    """Yield (tag, inner) for immediate children; tags may nest with the same name."""
    pos = 0
    length = len(inner)
    while pos < length:
        start = inner.find("<", pos)
        if start == -1:
            break
        if inner.startswith("</", start):
            break
        gt = inner.find(">", start)
        if gt == -1:
            break
        token = inner[start + 1 : gt].strip()
        if not token:
            pos = gt + 1
            continue
        if token.startswith("!"):
            pos = gt + 1
            continue
        if token.endswith("/"):
            pos = gt + 1
            continue
        if " " in token:
            token = token.split()[0]
        end = _find_matching_close(inner, token, gt + 1)
        if end is None:
            break
        yield token, inner[gt + 1 : end]
        pos = end + len(f"</{token}>")


def row_from_flat_xml(inner: str) -> dict[str, Any]:
    """Parse a flat ``<Col>text</Col>…`` fragment into a row dict."""
    row: dict[str, Any] = {}
    for tag, body in _iter_child_elements(inner):
        if not body:
            continue
        text = unescape(body)
        if text == "":
            continue
        row[tag] = coerce_xml_text(text)
    return row


def parse_transfer_bytes(data: bytes) -> dict[str, Any]:
    text = read_xml_bytes(data)
    edges: list[dict] = []
    object_map: list[dict] = []
    transfer_info: dict[str, str] = {}
    rows: dict[str, list[dict]] = {}
    found = False

    for block in iter_xmldata_blocks(text):
        found = True
        inner = block[len(_XMLDATA_OPEN) : -len(_XMLDATA_CLOSE)]
        for tag, body in _iter_child_elements(inner):
            row = row_from_flat_xml(body)
            if tag == "ObjectSetup":
                edges.append(row)
            elif tag == "ObjectMap":
                object_map.append(row)
            elif tag == "TransferInfo":
                transfer_info = row
            elif tag not in STRUCTURE_TAGS:
                rows.setdefault(tag, []).append(row)

    if not found:
        raise ValidationError("No <XMLData> blocks found")

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
    _by_id: dict[str, dict[int, dict]] = field(default_factory=dict, repr=False, compare=False)
    _groups: dict[tuple, dict[Any, list[dict]]] = field(
        default_factory=dict, repr=False, compare=False
    )

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
        idx._build_by_id()
        return idx

    def _build_by_id(self) -> None:
        by_id: dict[str, dict[int, dict]] = {}
        for table, table_rows in self.rows.items():
            id_col = f"{table}ID"
            mapping: dict[int, dict] = {}
            for row in table_rows:
                rid = _pk_int(row.get(id_col))
                if rid is not None:
                    mapping[rid] = row
            if mapping:
                by_id[table] = mapping
        self._by_id = by_id

    def _ensure_by_id(self) -> dict[str, dict[int, dict]]:
        if not self._by_id and self.rows:
            self._build_by_id()
        return self._by_id

    def row_by_id(self, table: str, row_id: int) -> dict | None:
        rid = _pk_int(row_id)
        if rid is None:
            return None
        mapping = self._ensure_by_id().get(table)
        if mapping is not None:
            return mapping.get(rid)
        id_col = f"{table}ID"
        for row in self.rows.get(table, []):
            if _pk_int(row.get(id_col)) == rid:
                return row
        return None

    def group_by(self, table: str, *cols: str) -> dict[Any, list[dict]]:
        """Group table rows by one or more columns (int-coerced when numeric)."""
        cache_key = (table, cols)
        cached = self._groups.get(cache_key)
        if cached is not None:
            return cached
        grouped: dict[Any, list[dict]] = defaultdict(list)
        for row in self.rows.get(table, []):
            parts = []
            skip = False
            for col in cols:
                raw = row.get(col)
                if raw is None:
                    skip = True
                    break
                parts.append(_group_key_part(raw))
            if skip:
                continue
            key = parts[0] if len(parts) == 1 else tuple(parts)
            grouped[key].append(row)
        as_dict = dict(grouped)
        self._groups[cache_key] = as_dict
        return as_dict

    def rows_for(self, table: str, col: str, value: Any) -> list[dict]:
        key = _group_key_part(value)
        return self.group_by(table, col).get(key, [])

    def rows_for_any(self, table: str, col: str, values: set[int]) -> list[dict]:
        if not values:
            return []
        grouped = self.group_by(table, col)
        out: list[dict] = []
        for value in values:
            out.extend(grouped.get(_group_key_part(value), []))
        return out

    def descendants(self, table: str, row_id: int) -> set[tuple[str, int]]:
        root = (table, row_id)
        seen: set[tuple[str, int]] = {root}
        queue: deque[tuple[str, int]] = deque([root])
        while queue:
            current = queue.popleft()
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
    by_id = index._ensure_by_id()
    for table in sorted(index.rows):
        mapping = by_id.get(table)
        if mapping:
            result[table] = max(mapping)
            continue
        id_col = f"{table}ID"
        max_id: int | None = None
        for row in index.rows.get(table) or []:
            parsed = _pk_int(row.get(id_col))
            if parsed is None:
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
