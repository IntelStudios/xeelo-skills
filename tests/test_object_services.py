"""Tests for ObjectService catalog bind and Client-Service calculation."""

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
        "object": {"name": "Company", "code": "COMPANY", "objectType": "Finance"},
        "company": {"name": "KB"},
        "objectServices": {
            "ares_name": {
                "name": "ARES Name",
                "type": "external",
                "link": "https://ares.example/api/parse?query={@1}&field=Name",
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
                                    "name": "ICO",
                                    "code": "ICO",
                                    "type": "text",
                                    "slot": 1,
                                    "width": 50,
                                    "order": 10,
                                },
                                {
                                    "name": "Company name",
                                    "code": "COMPANY_NAME",
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
        "templates": [
            {
                "key": "default",
                "name": "Default",
                "isDefault": True,
                "fields": {
                    "COMPANY_NAME": {
                        "clientCalculation": {
                            "type": "service",
                            "service": "ares_name",
                            "expr": "id{ICO}",
                        }
                    }
                },
            }
        ],
        "ids": {"base": 9200},
    }


class ObjectServiceGenerateTests(unittest.TestCase):
    def test_emits_external_service_and_binds_template_line(self) -> None:
        result = build_rows(_base_spec())
        self.assertEqual(len(result.rows["ObjectService"]), 1)
        svc = result.rows["ObjectService"][0]
        self.assertEqual(svc["ObjectServiceName"], "ARES Name")
        self.assertEqual(svc["ObjectServiceTypeID"], 1)
        self.assertEqual(
            svc["ObjectServiceLink"],
            "https://ares.example/api/parse?query={@1}&field=Name",
        )
        self.assertNotIn("ObjectServiceHeader", svc)
        self.assertNotIn("ObjectServiceSQL", svc)

        ico = next(r for r in result.rows["ObjectLine"] if r["ObjectLineCode"] == "ICO")
        name = next(
            r for r in result.rows["ObjectLine"] if r["ObjectLineCode"] == "COMPANY_NAME"
        )
        tpl = next(
            r
            for r in result.rows["ObjectDefaultLine"]
            if r["ObjectLineID"] == name["ObjectLineID"]
        )
        self.assertEqual(tpl["ObjectDefaultLineClientCalculationTypeID"], 3)
        self.assertEqual(
            tpl["ObjectDefaultLineClientCalculation"], f"id{ico['ObjectLineID']}"
        )
        self.assertEqual(tpl["ObjectServiceID"], svc["ObjectServiceID"])
        edges = {
            (e["TableName"], e["ChildTableName"], e["ChildTableRowID"]) for e in result.edges
        }
        self.assertIn(
            ("ObjectDefaultLine", "ObjectService", svc["ObjectServiceID"]),
            edges,
        )

    def test_unknown_key_raises(self) -> None:
        spec = _base_spec()
        spec["templates"][0]["fields"]["COMPANY_NAME"]["clientCalculation"][
            "service"
        ] = "missing"
        with self.assertRaises(ValueError) as ctx:
            build_rows(spec)
        self.assertIn("Unknown object service", str(ctx.exception))

    def test_missing_service_key_raises(self) -> None:
        spec = _base_spec()
        del spec["templates"][0]["fields"]["COMPANY_NAME"]["clientCalculation"]["service"]
        with self.assertRaises(ValueError) as ctx:
            build_rows(spec)
        self.assertIn("requires service", str(ctx.exception))

    def test_missing_link_raises(self) -> None:
        spec = _base_spec()
        spec["objectServices"]["ares_name"]["link"] = ""
        with self.assertRaises(ValueError) as ctx:
            build_rows(spec)
        self.assertIn("requires link", str(ctx.exception))

    def test_non_external_type_raises(self) -> None:
        spec = _base_spec()
        spec["objectServices"]["ares_name"]["type"] = "internal_sql"
        with self.assertRaises(ValueError) as ctx:
            build_rows(spec)
        self.assertIn("only 'external'", str(ctx.exception))

    def test_link_placeholders_not_compiled(self) -> None:
        spec = _base_spec()
        spec["objectServices"]["ares_name"]["link"] = (
            "https://host/api/parse?query={@1}&extra=id{ICO}"
        )
        result = build_rows(spec)
        svc = result.rows["ObjectService"][0]
        self.assertIn("{@1}", svc["ObjectServiceLink"])
        self.assertIn("id{ICO}", svc["ObjectServiceLink"])


class ObjectServiceRoundtripTests(unittest.TestCase):
    def test_extract_object_service_and_client_calc(self) -> None:
        spec = _base_spec()
        result = build_rows(spec)
        xml_bytes = build_object_transfer_xml(
            result.rows, dedupe_edges(result.edges), build_object_map(dedupe_edges(result.edges))
        )
        with tempfile.TemporaryDirectory() as tmp:
            xml_path = Path(tmp) / "ot.xml"
            xml_path.write_bytes(xml_bytes)
            extracted = extract_spec(xml_path)

        self.assertIn("objectServices", extracted)
        self.assertIn("ares_name", extracted["objectServices"])
        svc = extracted["objectServices"]["ares_name"]
        self.assertEqual(svc["type"], "external")
        self.assertEqual(
            svc["link"],
            "https://ares.example/api/parse?query={@1}&field=Name",
        )
        templates = extracted.get("templates") or []
        self.assertTrue(templates)
        calc = templates[0]["fields"]["COMPANY_NAME"]["clientCalculation"]
        self.assertEqual(calc["type"], "service")
        self.assertEqual(calc["service"], "ares_name")
        self.assertEqual(calc["expr"], "id{ICO}")
        self.assertIn("ares_name", extracted["ids"]["explicit"].get("objectServices") or {})

    def test_write_spec_splits_yaml(self) -> None:
        spec = _base_spec()
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "obj"
            write_spec(spec, directory)
            self.assertTrue((directory / "spec" / "object-services.yaml").is_file())
            loaded = load_spec(directory)
        self.assertIn("ares_name", loaded["objectServices"])
        self.assertEqual(
            loaded["objectServices"]["ares_name"]["link"],
            "https://ares.example/api/parse?query={@1}&field=Name",
        )
        calc = loaded["templates"][0]["fields"]["COMPANY_NAME"]["clientCalculation"]
        self.assertEqual(list(calc.keys())[0], "type")
        self.assertEqual(calc["service"], "ares_name")


if __name__ == "__main__":
    unittest.main()
