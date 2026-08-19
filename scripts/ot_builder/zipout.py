"""Write Object transfer ZIP (single XML entry)."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def write_zip(xml_bytes: bytes, zip_path: Path, entry_name: str = "object-transfer.xml") -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(zip_path, "w", ZIP_DEFLATED) as zf:
        zf.writestr(entry_name, xml_bytes)


def write_xml(xml_bytes: bytes, xml_path: Path) -> None:
    xml_path.parent.mkdir(parents=True, exist_ok=True)
    xml_path.write_bytes(xml_bytes)
