"""Generate/extract roundtrip for templates.fields.*.hint."""

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
from ot_builder.xml import build_object_transfer_xml  # noqa: E402


def _hint_spec(*, hint: str = "Hint for Title", extra_fields: list[dict] | None = None) -> dict:
    fields = [
        {
            "name": "Title",
            "code": "TITLE",
            "type": "text",
            "slot": 1,
            "width": 50,
            "order": 10,
        }
    ]
    if extra_fields:
        fields.extend(extra_fields)
    template_fields: dict = {"TITLE": {"hint": hint}}
    for field in extra_fields or []:
        code = field["code"]
        cfg = {}
        if field.get("type") != "empty_space" and "hint" in field:
            cfg["hint"] = field["hint"]
        if cfg:
            template_fields[code] = cfg
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
                            "fields": fields,
                        }
                    ],
                }
            ]
        },
        "templates": [
            {
                "key": "default",
                "name": "Default",
                "isDefault": True,
                "fields": template_fields,
            }
        ],
        "ids": {"base": 9300},
    }


class TemplateHintTests(unittest.TestCase):
    def test_emit_hint_on_template_line(self) -> None:
        result = build_rows(_hint_spec())
        title = next(r for r in result.rows["ObjectLine"] if r["ObjectLineCode"] == "TITLE")
        tl = next(
            r
            for r in result.rows["ObjectDefaultLine"]
            if r["ObjectLineID"] == title["ObjectLineID"]
        )
        self.assertEqual(tl["ObjectDefaultLineHint"], "Hint for Title")

    def test_hint_only_roundtrip_emits_templates(self) -> None:
        spec = _hint_spec()
        result = build_rows(spec)
        xml_bytes = build_object_transfer_xml(
            result.rows, dedupe_edges(result.edges), build_object_map(dedupe_edges(result.edges))
        )
        with tempfile.TemporaryDirectory() as tmp:
            xml_path = Path(tmp) / "ot.xml"
            xml_path.write_bytes(xml_bytes)
            extracted = extract_spec(xml_path)

        self.assertIn("templates", extracted)
        self.assertEqual(extracted["templates"][0]["fields"]["TITLE"]["hint"], "Hint for Title")

    def test_hint_rejected_on_empty_space(self) -> None:
        spec = _hint_spec()
        spec["layout"]["tabs"][0]["sections"][0]["fields"].append(
            {
                "name": "Gap",
                "code": "GAP",
                "type": "empty_space",
                "slot": 2,
                "order": 20,
            }
        )
        spec["templates"][0]["fields"]["GAP"] = {"hint": "Hint for Gap"}
        with self.assertRaises(ValueError) as ctx:
            build_rows(spec)
        self.assertIn("empty_space", str(ctx.exception))

    def test_hint_survives_client_calculation_absent(self) -> None:
        """hint must be written even when the template field has no clientCalculation."""
        result = build_rows(_hint_spec())
        tl = result.rows["ObjectDefaultLine"][0]
        self.assertEqual(tl["ObjectDefaultLineHint"], "Hint for Title")
        self.assertNotIn("ObjectDefaultLineClientCalculationTypeID", tl)


class FieldIsActiveTests(unittest.TestCase):
    def test_generate_and_extract_inactive_line(self) -> None:
        spec = _hint_spec()
        spec["layout"]["tabs"][0]["sections"][0]["fields"].append(
            {
                "name": "Update",
                "code": "BTN_UPDATE",
                "type": "button",
                "slot": 10,
                "width": 50,
                "order": 20,
                "isActive": False,
            }
        )
        result = build_rows(spec)
        by_code = {r["ObjectLineCode"]: r for r in result.rows["ObjectLine"]}
        self.assertEqual(by_code["TITLE"]["IsActive"], 1)
        self.assertEqual(by_code["BTN_UPDATE"]["IsActive"], 0)
        xml_bytes = build_object_transfer_xml(
            result.rows, dedupe_edges(result.edges), build_object_map(dedupe_edges(result.edges))
        )
        with tempfile.TemporaryDirectory() as tmp:
            xml_path = Path(tmp) / "ot.xml"
            xml_path.write_bytes(xml_bytes)
            extracted = extract_spec(xml_path)
        fields = extracted["layout"]["tabs"][0]["sections"][0]["fields"]
        by_extracted = {f["code"]: f for f in fields}
        self.assertNotIn("isActive", by_extracted["TITLE"])
        self.assertFalse(by_extracted["BTN_UPDATE"]["isActive"])
