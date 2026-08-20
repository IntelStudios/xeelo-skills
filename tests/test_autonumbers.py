"""Tests for autonumber catalog bind and ObjectLine unique level."""

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
from ot_builder.spec_loader import load_spec, write_spec  # noqa: E402
from ot_builder.xml import build_object_transfer_xml  # noqa: E402


def _base_spec() -> dict:
    return {
        "version": 2,
        "kind": "create_object",
        "object": {"name": "Sink", "code": "SINK", "objectType": "Finance"},
        "company": {"name": "KB"},
        "autonumbers": {
            "request_number": {
                "description": "Request number",
                "format": "REQ####",
                "next": 1,
            }
        },
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
                                    "name": "Request number",
                                    "code": "REQUEST_NO",
                                    "type": "text",
                                    "slot": 1,
                                    "width": 50,
                                    "order": 10,
                                    "uniqueId": 1,
                                    "autonumber": "request_number",
                                },
                                {
                                    "name": "Note",
                                    "code": "NOTE",
                                    "type": "text",
                                    "slot": 2,
                                    "width": 50,
                                    "order": 20,
                                },
                            ],
                        }
                    ],
                }
            ]
        },
        "ids": {"base": 9100},
    }


class AutonumberGenerateTests(unittest.TestCase):
    def test_unique_sets_id_and_bit(self) -> None:
        result = build_rows(_base_spec())
        line = next(r for r in result.rows["ObjectLine"] if r["ObjectLineCode"] == "REQUEST_NO")
        self.assertEqual(line["ObjectLineUniqueID"], 1)
        self.assertEqual(line["ObjectLineIsUnique"], 1)
        note = next(r for r in result.rows["ObjectLine"] if r["ObjectLineCode"] == "NOTE")
        self.assertNotIn("ObjectLineUniqueID", note)
        self.assertNotIn("ObjectLineIsUnique", note)

    def test_binds_autonumber_on_template_line(self) -> None:
        result = build_rows(_base_spec())
        self.assertEqual(len(result.rows["ObjectLineAutoNumber"]), 1)
        an = result.rows["ObjectLineAutoNumber"][0]
        self.assertEqual(an["ObjectLineAutoNumberFormat"], "REQ####")
        self.assertEqual(an["ObjectLineAutoNumberNext"], 1)
        self.assertEqual(an["ObjectLineAutoNumberDescription"], "Request number")
        line = next(r for r in result.rows["ObjectLine"] if r["ObjectLineCode"] == "REQUEST_NO")
        tpl = next(
            r
            for r in result.rows["ObjectDefaultLine"]
            if r["ObjectLineID"] == line["ObjectLineID"]
        )
        self.assertEqual(tpl["ObjectDefaultLineAutoNumberID"], an["ObjectLineAutoNumberID"])
        edges = {
            (e["TableName"], e["ChildTableName"], e["ChildTableRowID"]) for e in result.edges
        }
        self.assertIn(
            ("ObjectDefaultLine", "ObjectLineAutoNumber", an["ObjectLineAutoNumberID"]),
            edges,
        )

    def test_templates_fields_autonumber(self) -> None:
        spec = _base_spec()
        del spec["layout"]["tabs"][0]["sections"][0]["fields"][0]["autonumber"]
        spec["templates"] = [
            {
                "key": "default",
                "name": "Default",
                "isDefault": True,
                "fields": {
                    "REQUEST_NO": {"autonumber": "request_number", "alwaysDisabled": True},
                },
            }
        ]
        result = build_rows(spec)
        line = next(r for r in result.rows["ObjectLine"] if r["ObjectLineCode"] == "REQUEST_NO")
        tpl = next(
            r
            for r in result.rows["ObjectDefaultLine"]
            if r["ObjectLineID"] == line["ObjectLineID"]
        )
        self.assertTrue(tpl.get("ObjectDefaultLineAutoNumberID"))
        self.assertEqual(tpl["ObjectDefaultLineIsDisabled"], 1)

    def test_yearly_reset(self) -> None:
        spec = _base_spec()
        spec["autonumbers"]["request_number"]["resetTypeId"] = 1
        result = build_rows(spec)
        an = result.rows["ObjectLineAutoNumber"][0]
        self.assertEqual(an["ObjectLineAutoNumberResetTypeID"], 1)

    def test_unknown_key_raises(self) -> None:
        spec = _base_spec()
        spec["layout"]["tabs"][0]["sections"][0]["fields"][0]["autonumber"] = "missing"
        with self.assertRaises(ValueError) as ctx:
            build_rows(spec)
        self.assertIn("Unknown autonumber", str(ctx.exception))

    def test_non_text_raises(self) -> None:
        spec = _base_spec()
        spec["layout"]["tabs"][0]["sections"][0]["fields"][0]["type"] = "number"
        spec["layout"]["tabs"][0]["sections"][0]["fields"][0]["precision"] = 0
        with self.assertRaises(ValueError) as ctx:
            build_rows(spec)
        self.assertIn("type text", str(ctx.exception))


class AutonumberRoundtripTests(unittest.TestCase):
    def test_extract_autonumber_and_unique(self) -> None:
        spec = _base_spec()
        result = build_rows(spec)
        xml_bytes = build_object_transfer_xml(
            result.rows, dedupe_edges(result.edges), build_object_map(dedupe_edges(result.edges))
        )
        with tempfile.TemporaryDirectory() as tmp:
            xml_path = Path(tmp) / "ot.xml"
            xml_path.write_bytes(xml_bytes)
            extracted = extract_spec(xml_path)

        self.assertIn("autonumbers", extracted)
        self.assertIn("request_number", extracted["autonumbers"])
        self.assertEqual(extracted["autonumbers"]["request_number"]["format"], "REQ####")
        fields = {
            f["code"]: f
            for tab in extracted["layout"]["tabs"]
            for sec in tab["sections"]
            for f in sec["fields"]
        }
        self.assertEqual(fields["REQUEST_NO"]["uniqueId"], 1)
        templates = extracted.get("templates") or []
        self.assertTrue(templates)
        request_cfg = templates[0]["fields"]["REQUEST_NO"]
        self.assertEqual(request_cfg["autonumber"], "request_number")
        self.assertIn("request_number", extracted["ids"]["explicit"].get("autonumbers") or {})

    def test_write_spec_splits_yaml(self) -> None:
        spec = _base_spec()
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "obj"
            write_spec(spec, directory)
            self.assertTrue((directory / "spec" / "autonumbers.yaml").is_file())
            loaded = load_spec(directory)
        self.assertIn("request_number", loaded["autonumbers"])
        self.assertEqual(loaded["autonumbers"]["request_number"]["format"], "REQ####")


if __name__ == "__main__":
    unittest.main()
