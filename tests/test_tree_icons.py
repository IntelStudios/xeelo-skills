"""Tests for tree icon / CustomColorCode emit and extract."""

from __future__ import annotations

import json
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
        "object": {
            "name": "Account",
            "code": "ACCOUNT",
            "objectType": "Finance",
            "icon": "fa-university fa-solid fa-fw",
            "color": "blue",
        },
        "objectType": {
            "icon": "fa-coins fa-solid fa-fw",
            "color": "blue-steel",
        },
        "company": {
            "name": "KB",
            "icon": "fa-building fa-solid fa-fw",
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
                                    "name": "Title",
                                    "code": "TITLE",
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
        "ids": {"base": 9200},
    }


class TreeIconGenerateTests(unittest.TestCase):
    def test_emits_live_tree_columns(self) -> None:
        result = build_rows(_base_spec())
        company = result.rows["Company"][0]
        object_type = result.rows["ObjectType"][0]
        obj = result.rows["Object"][0]

        self.assertEqual(company["CompanyTreeIcon"], "fa-building fa-solid fa-fw")
        self.assertNotIn("CompanyTreeColor", company)

        self.assertEqual(object_type["ObjectTypeTreeIcon"], "fa-coins fa-solid fa-fw")
        self.assertEqual(object_type["ObjectTypeTreeColorBack"], "blue-steel")
        self.assertNotIn("ObjectTypeTreeColorFont", object_type)

        self.assertEqual(obj["ObjectTreeIcon"], "fa-university fa-solid fa-fw")
        self.assertEqual(obj["ObjectTreeColor"], "blue")

    def test_omits_empty_icon_and_color(self) -> None:
        spec = _base_spec()
        spec["object"]["icon"] = "  "
        spec["object"]["color"] = None
        spec["objectType"] = {}
        spec["company"].pop("icon")
        result = build_rows(spec)
        self.assertNotIn("ObjectTreeIcon", result.rows["Object"][0])
        self.assertNotIn("ObjectTreeColor", result.rows["Object"][0])
        self.assertNotIn("ObjectTypeTreeIcon", result.rows["ObjectType"][0])
        self.assertNotIn("ObjectTypeTreeColorBack", result.rows["ObjectType"][0])
        self.assertNotIn("CompanyTreeIcon", result.rows["Company"][0])

    def test_color_is_custom_color_code_not_hex(self) -> None:
        result = build_rows(_base_spec())
        self.assertEqual(result.rows["Object"][0]["ObjectTreeColor"], "blue")
        self.assertNotIn("#", result.rows["Object"][0]["ObjectTreeColor"])
        self.assertEqual(result.rows["ObjectType"][0]["ObjectTypeTreeColorBack"], "blue-steel")

    def test_write_spec_keeps_object_type_in_object_fragment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            write_spec(_base_spec(), Path(tmp) / "obj")
            text = (Path(tmp) / "obj" / "spec" / "object.yaml").read_text(encoding="utf-8")
            self.assertIn("objectType:", text)
            self.assertIn("blue-steel", text)
            self.assertIn("fa-university", text)
            self.assertIn("fa-building", text)


class TreeIconRoundtripTests(unittest.TestCase):
    def test_extract_rebuilds_icon_and_color(self) -> None:
        spec = _base_spec()
        result = build_rows(spec)
        xml_bytes = build_object_transfer_xml(
            result.rows, dedupe_edges(result.edges), build_object_map(dedupe_edges(result.edges))
        )
        with tempfile.TemporaryDirectory() as tmp:
            xml_path = Path(tmp) / "ot.xml"
            xml_path.write_bytes(xml_bytes)
            extracted = extract_spec(xml_path)

        self.assertEqual(extracted["object"]["icon"], "fa-university fa-solid fa-fw")
        self.assertEqual(extracted["object"]["color"], "blue")
        self.assertEqual(extracted["object"]["objectType"], "Finance")
        self.assertNotIn("objectTypeColor", extracted["object"])
        self.assertEqual(extracted["objectType"]["icon"], "fa-coins fa-solid fa-fw")
        self.assertEqual(extracted["objectType"]["color"], "blue-steel")
        self.assertEqual(extracted["company"]["icon"], "fa-building fa-solid fa-fw")
        self.assertNotIn("color", extracted["company"])


class CustomColorSeedTests(unittest.TestCase):
    def test_seed_has_codes_not_hex_keys(self) -> None:
        path = ROOT / "data" / "enums" / "CustomColor.json"
        rows = json.loads(path.read_text(encoding="utf-8"))
        by_code = {row["code"]: row for row in rows}
        self.assertIn("blue", by_code)
        self.assertEqual(by_code["blue"]["hex"], "#3598dc")
        self.assertFalse(by_code["blue"]["isDefault"])
        self.assertIn("blue-steel", by_code)
        self.assertTrue(by_code["base-dark"]["isDefault"])


if __name__ == "__main__":
    unittest.main()
