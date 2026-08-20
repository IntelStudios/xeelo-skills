"""Tests for lookup query maps, references.yaml split, and source aliases."""

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
        "references": {
            "ks_kind": {
                "name": "Kind",
                "typeId": 1,
                "styleId": 4,
                "values": [
                    {"value": "demo", "label": "Demo"},
                    {"value": "full", "label": "Full"},
                ],
            },
            "ks_priority": {
                "name": "Priority",
                "typeId": 1,
                "styleId": 4,
                "values": [
                    {"value": "LOW", "label": "Low"},
                    {"value": "MED", "label": "Medium"},
                    {"value": "HIGH", "label": "High"},
                ],
            },
        },
        "lookups": {
            "priority_by_kind": {
                "name": "Priority by kind",
                "values": [
                    {"source": "demo", "return": "LOW"},
                    {"source": "full", "return": "HIGH"},
                ],
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
                                    "name": "Kind",
                                    "code": "ks_kind",
                                    "type": "combobox",
                                    "slot": 1,
                                    "width": 50,
                                    "order": 10,
                                    "reference": {"reference": "ks_kind"},
                                },
                                {
                                    "name": "Flag",
                                    "code": "ks_flag",
                                    "type": "text",
                                    "slot": 2,
                                    "width": 50,
                                    "order": 20,
                                },
                                {
                                    "name": "Priority",
                                    "code": "ks_priority",
                                    "type": "combobox",
                                    "slot": 3,
                                    "width": 50,
                                    "order": 30,
                                    "reference": {"reference": "ks_priority"},
                                    "lookup": {
                                        "lookup": "priority_by_kind",
                                        "sourceField": "ks_kind",
                                    },
                                },
                                {
                                    "name": "Title",
                                    "code": "ks_title",
                                    "type": "text",
                                    "slot": 4,
                                    "width": 50,
                                    "order": 40,
                                    "lookup": {
                                        "lookup": "priority_by_kind",
                                        "sourceField": "ks_kind",
                                    },
                                },
                            ],
                        }
                    ],
                }
            ]
        },
        "ids": {"base": 9100},
    }


class LookupGenerateTests(unittest.TestCase):
    def test_combo_may_have_reference_and_lookup(self) -> None:
        result = build_rows(_base_spec())
        priority = next(r for r in result.rows["ObjectLine"] if r["ObjectLineCode"] == "ks_priority")
        self.assertTrue(priority.get("ObjectLineSourceID"))
        tpl = next(
            r
            for r in result.rows["ObjectDefaultLine"]
            if r["ObjectLineID"] == priority["ObjectLineID"]
        )
        self.assertTrue(tpl.get("ObjectDefaultLineLookupID"))
        kind = next(r for r in result.rows["ObjectLine"] if r["ObjectLineCode"] == "ks_kind")
        self.assertEqual(tpl["ObjectDefaultLineLookupObjectLineID"], kind["ObjectLineID"])

    def test_shared_lookup_emits_one_map(self) -> None:
        result = build_rows(_base_spec())
        self.assertEqual(len(result.rows["ObjectLineLookup"]), 1)
        returns = {r["ObjectLineLookupReturnValue"] for r in result.rows["ObjectLineLookupValue"]}
        self.assertEqual(returns, {"LOW", "HIGH"})
        title = next(r for r in result.rows["ObjectLine"] if r["ObjectLineCode"] == "ks_title")
        tpl = next(
            r
            for r in result.rows["ObjectDefaultLine"]
            if r["ObjectLineID"] == title["ObjectLineID"]
        )
        self.assertEqual(
            tpl["ObjectDefaultLineLookupID"],
            result.rows["ObjectLineLookup"][0]["ObjectLineLookupID"],
        )

    def test_lookup_filter_field(self) -> None:
        spec = _base_spec()
        spec["lookups"]["priority_by_kind"]["values"] = [
            {"source": "demo", "return": "LOW", "filter": "x"},
            {"source": "full", "return": "HIGH", "filter": "x"},
        ]
        spec["layout"]["tabs"][0]["sections"][0]["fields"][2]["lookup"]["filterField"] = "ks_flag"
        result = build_rows(spec)
        priority = next(r for r in result.rows["ObjectLine"] if r["ObjectLineCode"] == "ks_priority")
        flag = next(r for r in result.rows["ObjectLine"] if r["ObjectLineCode"] == "ks_flag")
        tpl = next(
            r
            for r in result.rows["ObjectDefaultLine"]
            if r["ObjectLineID"] == priority["ObjectLineID"]
        )
        self.assertEqual(tpl["ObjectDefaultLineLookupFilterObjectLineID"], flag["ObjectLineID"])
        self.assertEqual(
            {r["ObjectLineLookupFilterValue"] for r in result.rows["ObjectLineLookupValue"]},
            {"x"},
        )

    def test_sources_alias_still_builds(self) -> None:
        spec = _base_spec()
        spec["sources"] = spec.pop("references")
        spec["layout"]["tabs"][0]["sections"][0]["fields"][0]["reference"] = {"source": "ks_kind"}
        spec["layout"]["tabs"][0]["sections"][0]["fields"][2]["reference"] = {"source": "ks_priority"}
        result = build_rows(spec)
        self.assertEqual(len(result.rows["ObjectLineSource"]), 2)

    def test_lookup_requires_source_field(self) -> None:
        spec = _base_spec()
        del spec["layout"]["tabs"][0]["sections"][0]["fields"][2]["lookup"]["sourceField"]
        with self.assertRaises(ValueError) as ctx:
            build_rows(spec)
        self.assertIn("sourceField", str(ctx.exception))


class LookupRoundtripTests(unittest.TestCase):
    def test_extract_named_lookup_and_references(self) -> None:
        spec = _base_spec()
        result = build_rows(spec)
        xml_bytes = build_object_transfer_xml(
            result.rows, dedupe_edges(result.edges), build_object_map(dedupe_edges(result.edges))
        )
        with tempfile.TemporaryDirectory() as tmp:
            xml_path = Path(tmp) / "ot.xml"
            xml_path.write_bytes(xml_bytes)
            extracted = extract_spec(xml_path)

        self.assertIn("references", extracted)
        self.assertIn("lookups", extracted)
        self.assertNotIn("sources", extracted)
        fields = {
            f["code"]: f
            for tab in extracted["layout"]["tabs"]
            for sec in tab["sections"]
            for f in sec["fields"]
        }
        priority = fields["ks_priority"]
        self.assertIn("reference", priority)
        self.assertIn("reference", priority["reference"])
        self.assertEqual(priority["lookup"]["sourceField"], "ks_kind")
        lookup_key = priority["lookup"]["lookup"]
        self.assertEqual(fields["ks_title"]["lookup"]["lookup"], lookup_key)
        values = {v["source"]: v["return"] for v in extracted["lookups"][lookup_key]["values"]}
        self.assertEqual(values["demo"], "LOW")
        self.assertEqual(values["full"], "HIGH")

    def test_write_spec_splits_yaml(self) -> None:
        spec = _base_spec()
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "obj"
            write_spec(spec, directory)
            self.assertTrue((directory / "spec" / "references.yaml").is_file())
            self.assertTrue((directory / "spec" / "lookups.yaml").is_file())
            loaded = load_spec(directory)
        self.assertIn("ks_priority", loaded["references"])
        self.assertIn("priority_by_kind", loaded["lookups"])
        self.assertNotIn("sources", loaded)


if __name__ == "__main__":
    unittest.main()
