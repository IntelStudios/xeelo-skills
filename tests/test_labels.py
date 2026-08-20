"""Tests for spec languageTable → LanguageTable emit/extract."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ot_builder.extract import extract_spec  # noqa: E402
from ot_builder.hierarchy import build_object_map, dedupe_edges  # noqa: E402
from ot_builder.rows import build_rows  # noqa: E402
from ot_builder.spec_loader import write_spec  # noqa: E402
from ot_builder.xml import build_object_transfer_xml  # noqa: E402


def _base_spec() -> dict:
    return {
        "version": 2,
        "kind": "create_object",
        "object": {"name": "Sink", "code": "SINK", "objectType": "Finance"},
        "company": {"name": "KB"},
        "layout": {
            "tabs": [
                {
                    "name": "General",
                    "placement": 0,
                    "order": 10,
                    "sections": [
                        {
                            "name": "Main",
                            "order": 10,
                            "width": 100,
                            "fields": [
                                {
                                    "name": "Title",
                                    "code": "ks_title",
                                    "type": "text",
                                    "slot": 1,
                                    "width": 50,
                                    "order": 10,
                                }
                            ],
                        }
                    ],
                }
            ]
        },
        "languageTable": {
            "object": {"cs": "Dřez"},
            "tabs": {"General": {"cs": "Obecné"}},
            "sections": {"General/Main": {"cs": "Hlavní"}},
            "lines": {"ks_title": {"cs": "Název"}},
        },
        "ids": {"base": 9200},
    }


class LanguageTableGenerateTests(unittest.TestCase):
    def test_emits_language_table_rows_and_edges(self) -> None:
        result = build_rows(_base_spec())
        rows = result.rows["LanguageTable"]
        self.assertEqual(len(rows), 4)
        by_col = {(r["TableName"], r["ColumnName"], r["UserLanguageCode"]): r for r in rows}
        self.assertEqual(by_col[("Object", "ObjectName", "cs")]["LanguageTableData"], "Dřez")
        self.assertEqual(by_col[("ObjectLineTab", "ObjectLineTabName", "cs")]["LanguageTableData"], "Obecné")
        self.assertEqual(
            by_col[("ObjectLineSection", "ObjectSectionName", "cs")]["LanguageTableData"], "Hlavní"
        )
        self.assertEqual(by_col[("ObjectLine", "ObjectLineName", "cs")]["LanguageTableData"], "Název")

        object_id = result.rows["Object"][0]["ObjectID"]
        title = next(r for r in result.rows["ObjectLine"] if r["ObjectLineCode"] == "ks_title")
        title_lt = by_col[("ObjectLine", "ObjectLineName", "cs")]
        self.assertEqual(title_lt["RowID"], str(title["ObjectLineID"]))
        self.assertIn(
            {
                "TableName": "ObjectLine",
                "TableRowID": title["ObjectLineID"],
                "ChildTableName": "LanguageTable",
                "ChildTableRowID": title_lt["LanguageTableID"],
            },
            result.edges,
        )
        self.assertIn(
            {
                "TableName": "Object",
                "TableRowID": object_id,
                "ChildTableName": "LanguageTable",
                "ChildTableRowID": by_col[("Object", "ObjectName", "cs")]["LanguageTableID"],
            },
            result.edges,
        )

        object_map = build_object_map(dedupe_edges(result.edges))
        pairs = {(p["TableName"], p["ChildTableName"]) for p in object_map}
        self.assertIn(("Object", "LanguageTable"), pairs)
        self.assertIn(("ObjectLine", "LanguageTable"), pairs)
        self.assertIn(("ObjectLineTab", "LanguageTable"), pairs)
        self.assertIn(("ObjectLineSection", "LanguageTable"), pairs)

    def test_line_on_grid_translation(self) -> None:
        spec = _base_spec()
        spec["languageTable"]["lines"]["ks_title"]["onGrid"] = {"cs": "Náz."}
        result = build_rows(spec)
        grid = next(
            r
            for r in result.rows["LanguageTable"]
            if r["ColumnName"] == "ObjectLineOnGridName"
        )
        self.assertEqual(grid["LanguageTableData"], "Náz.")
        self.assertEqual(grid["UserLanguageCode"], "cs")

    def test_unknown_line_raises(self) -> None:
        spec = _base_spec()
        spec["languageTable"]["lines"]["missing"] = {"cs": "Chybí"}
        with self.assertRaises(ValueError) as ctx:
            build_rows(spec)
        self.assertIn("missing", str(ctx.exception))

    def test_write_spec_fragment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            entry = write_spec(_base_spec(), Path(tmp) / "obj")
            lang_path = Path(tmp) / "obj" / "spec" / "language-table.yaml"
            self.assertTrue(lang_path.is_file())
            text = lang_path.read_text(encoding="utf-8")
            self.assertIn("languageTable:", text)
            self.assertIn("ks_title:", text)
            includes = entry.read_text(encoding="utf-8")
            self.assertIn("spec/language-table.yaml", includes)


class LanguageTableRoundtripTests(unittest.TestCase):
    def test_extract_rebuilds_language_table(self) -> None:
        spec = _base_spec()
        result = build_rows(spec)
        xml_bytes = build_object_transfer_xml(
            result.rows, dedupe_edges(result.edges), build_object_map(dedupe_edges(result.edges))
        )
        with tempfile.TemporaryDirectory() as tmp:
            xml_path = Path(tmp) / "ot.xml"
            xml_path.write_bytes(xml_bytes)
            extracted = extract_spec(xml_path)

        self.assertEqual(extracted["languageTable"]["object"]["cs"], "Dřez")
        self.assertEqual(extracted["languageTable"]["tabs"]["General"]["cs"], "Obecné")
        self.assertEqual(extracted["languageTable"]["sections"]["General/Main"]["cs"], "Hlavní")
        self.assertEqual(extracted["languageTable"]["lines"]["ks_title"]["cs"], "Název")
        self.assertIn("languageTables", extracted["ids"]["explicit"])
        self.assertTrue(extracted["ids"]["explicit"]["languageTables"])
