"""Validate Xeelo Object transfer XML/ZIP format (upload SP compatibility)."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

EXPECTED_VERSION = "1.3.0"
STRUCTURE_BLOCKS = ("ObjectSetup", "ObjectMap", "TransferInfo")


class ValidationError(Exception):
    pass


def read_xml_bytes(data: bytes) -> str:
    if data[:2] == b"\xff\xfe":
        return data.decode("utf-16-le")
    if data[:2] == b"\xfe\xff":
        return data.decode("utf-16-be")
    if data.startswith(b"<?xml"):
        return data.decode("utf-8")
    return data.decode("utf-8")


def extract_block_name(block: str) -> str:
    """Simulate spAdminObjectSetupXMLUpload table-name extraction."""
    prefix = block[:255].replace("<XMLData><", "")
    gt = prefix.find(">")
    if gt == -1:
        raise ValidationError(f"Invalid XMLData block prefix: {prefix[:80]!r}")
    return prefix[:gt]


def iter_xmldata_blocks(text: str):
    """Yield each ``<XMLData>…</XMLData>`` block without materializing them all."""
    found = False
    for match in re.finditer(r"<XMLData>.*?</XMLData>", text, re.DOTALL):
        found = True
        yield match.group(0)
    if not found:
        raise ValidationError("No <XMLData> blocks found")


def split_xmldata_blocks(text: str) -> list[str]:
    return list(iter_xmldata_blocks(text))


def validate_transfer_info(block: str) -> None:
    root = ET.fromstring(block)
    transfer = root.find("TransferInfo")
    if transfer is None:
        raise ValidationError("TransferInfo block missing TransferInfo element")
    transfer_type = transfer.findtext("TransferType")
    version = transfer.findtext("Version")
    if transfer_type != "OBJECT":
        raise ValidationError(f"TransferType must be OBJECT, got {transfer_type!r}")
    if version != EXPECTED_VERSION:
        raise ValidationError(f"Version must be {EXPECTED_VERSION}, got {version!r}")


def validate_data_block(block: str, index: int) -> None:
    root = ET.fromstring(block)
    tags = {child.tag for child in root}
    if not tags:
        raise ValidationError(f"Data block {index} is empty")
    if len(tags) > 1:
        raise ValidationError(f"Data block {index} mixes element types: {sorted(tags)}")
    if tags & set(STRUCTURE_BLOCKS):
        raise ValidationError(f"Data block {index} contains structure element: {tags}")


def validate_object_transfer_xml(data: bytes, source: str = "<bytes>") -> None:
    if data[:2] not in (b"\xff\xfe", b"\xfe\xff"):
        raise ValidationError(f"{source}: expected UTF-16 LE/BE with BOM")

    text = read_xml_bytes(data)
    if "<?xml" in text[:100]:
        raise ValidationError(f"{source}: XML declaration should not be present (Xeelo format)")

    blocks = split_xmldata_blocks(text)
    if len(blocks) < 4:
        raise ValidationError(f"{source}: expected at least 4 XMLData blocks, got {len(blocks)}")

    for idx, expected in enumerate(STRUCTURE_BLOCKS):
        name = extract_block_name(blocks[idx])
        if name != expected:
            raise ValidationError(f"{source}: block {idx} should be {expected}, got {name!r}")

    validate_transfer_info(blocks[2])

    for idx, block in enumerate(blocks[3:], start=3):
        validate_data_block(block, idx)


def validate_path(path: Path) -> None:
    if path.suffix.lower() == ".zip":
        with ZipFile(path) as zf:
            for info in zf.infolist():
                if info.filename.endswith("/"):
                    continue
                validate_object_transfer_xml(zf.read(info.filename), f"{path}:{info.filename}")
    else:
        validate_object_transfer_xml(path.read_bytes(), str(path))
