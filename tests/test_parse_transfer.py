"""Parser for concatenated XMLData transfer blocks (no ElementTree DOM)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ot_builder.parse import (  # noqa: E402
    TransferIndex,
    coerce_xml_text,
    parse_transfer_bytes,
    row_from_flat_xml,
)


def _utf16(*blocks: str) -> bytes:
    return "".join(f"<XMLData>{block}</XMLData>" for block in blocks).encode("utf-16")


class CoerceXmlTextTests(unittest.TestCase):
    def test_int_and_negative(self) -> None:
        self.assertEqual(coerce_xml_text("12"), 12)
        self.assertEqual(coerce_xml_text("-5"), -5)
        self.assertIsInstance(coerce_xml_text("12"), int)

    def test_version_stays_string(self) -> None:
        self.assertEqual(coerce_xml_text("1.3.0"), "1.3.0")

    def test_float(self) -> None:
        self.assertEqual(coerce_xml_text("1.5"), 1.5)


class RowFromFlatXmlTests(unittest.TestCase):
    def test_skips_empty_and_unescapes(self) -> None:
        row = row_from_flat_xml(
            "<ObjectID>10</ObjectID><Empty></Empty><Name>A &amp; B &lt;C&gt;</Name>"
        )
        self.assertEqual(row["ObjectID"], 10)
        self.assertNotIn("Empty", row)
        self.assertEqual(row["Name"], "A & B <C>")

    def test_nested_same_name_as_table(self) -> None:
        data = _utf16(
            "<TransferInfo><TransferType>DB</TransferType><Version>1.3.0</Version></TransferInfo>",
            "<ObjectLineSourceValue>"
            "<ObjectLineSourceValueID>1</ObjectLineSourceValueID>"
            "<ObjectLineSourceID>2</ObjectLineSourceID>"
            "<ObjectLineSourceValue>yes</ObjectLineSourceValue>"
            "<ObjectLineSourceValueName>Yes</ObjectLineSourceValueName>"
            "</ObjectLineSourceValue>",
        )
        parsed = parse_transfer_bytes(data)
        row = parsed["rows"]["ObjectLineSourceValue"][0]
        self.assertEqual(row["ObjectLineSourceValueID"], 1)
        self.assertEqual(row["ObjectLineSourceValue"], "yes")
        self.assertEqual(row["ObjectLineSourceValueName"], "Yes")


class ParseTransferBytesTests(unittest.TestCase):
    def test_db_blocks_and_types(self) -> None:
        data = _utf16(
            "<TransferInfo><TransferType>DB</TransferType><Version>1.3.0</Version></TransferInfo>",
            "<Object><ObjectID>-7</ObjectID><ObjectName>Cars</ObjectName></Object>"
            "<Object><ObjectID>8</ObjectID><ObjectName>A &amp; B</ObjectName></Object>",
        )
        parsed = parse_transfer_bytes(data)
        self.assertEqual(parsed["transferInfo"]["TransferType"], "DB")
        self.assertEqual(parsed["transferInfo"]["Version"], "1.3.0")
        self.assertEqual(parsed["rows"]["Object"][0]["ObjectID"], -7)
        self.assertEqual(parsed["rows"]["Object"][1]["ObjectName"], "A & B")
        self.assertEqual(parsed["edges"], [])

    def test_object_setup_edges(self) -> None:
        data = _utf16(
            "<ObjectSetup><TableName>Object</TableName><TableRowID>1</TableRowID>"
            "<ChildTableName>ObjectLine</ChildTableName><ChildTableRowID>2</ChildTableRowID>"
            "</ObjectSetup>",
            "<ObjectMap><TableName>Object</TableName><ChildTableName>ObjectLine</ChildTableName></ObjectMap>",
            "<TransferInfo><TransferType>OBJECT</TransferType><Version>1.3.0</Version></TransferInfo>",
        )
        parsed = parse_transfer_bytes(data)
        self.assertEqual(parsed["edges"][0]["TableRowID"], 1)
        self.assertEqual(parsed["objectMap"][0]["ChildTableName"], "ObjectLine")

    def test_index_pk_and_fk(self) -> None:
        parsed = parse_transfer_bytes(
            _utf16(
                "<TransferInfo><TransferType>DB</TransferType><Version>1.3.0</Version></TransferInfo>",
                "<ObjectLine><ObjectLineID>3</ObjectLineID><ObjectID>9</ObjectID>"
                "<ObjectLineCode>TITLE</ObjectLineCode></ObjectLine>"
                "<ObjectLine><ObjectLineID>4</ObjectLineID><ObjectID>9</ObjectID>"
                "<ObjectLineCode>AMOUNT</ObjectLineCode></ObjectLine>",
            )
        )
        index = TransferIndex.from_parsed(parsed)
        self.assertEqual(index.row_by_id("ObjectLine", 4)["ObjectLineCode"], "AMOUNT")
        self.assertEqual(len(index.rows_for("ObjectLine", "ObjectID", 9)), 2)
        self.assertEqual(index.rows_for("ObjectLine", "ObjectID", 1), [])
