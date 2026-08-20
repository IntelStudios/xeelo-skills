"""Tests for ObjectMessage generate/extract."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ot_builder.extract import extract_spec  # noqa: E402
from ot_builder.hierarchy import build_object_map, dedupe_edges  # noqa: E402
from ot_builder.object_messages import HTML_DB_COLUMN  # noqa: E402
from ot_builder.rows import build_rows  # noqa: E402
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
                                    "name": "Name",
                                    "code": "NAME",
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
        "ids": {"base": 9300},
    }


class ObjectMessageGenerateTests(unittest.TestCase):
    def test_emits_message_row_and_update_link(self) -> None:
        spec = _base_spec()
        spec["objectMessages"] = [
            {
                "key": "retag_payments",
                "name": "Retag payments",
                "style": "warning",
                "order": 10,
                "html": "<p>All payments will be retagged.</p>",
            }
        ]
        spec["updateActions"] = [
            {
                "key": "update",
                "name": "Update",
                "order": 10,
                "access": [{"field": "NAME", "editable": True}],
                "messages": [{"key": "retag_payments", "visible": True}],
            }
        ]
        spec["languageTable"] = {
            "objectMessages": {
                "retag_payments": {
                    "cs": "Přestítkovat platby",
                    "html": {"cs": "<p>Přestítkují se všechny platby.</p>"},
                }
            }
        }
        result = build_rows(spec)
        om = result.rows["ObjectMessage"][0]
        self.assertEqual(om["ObjectMessageName"], "Retag payments")
        self.assertEqual(om["ObjectMessageStyleID"], 2)
        self.assertEqual(om[HTML_DB_COLUMN], "<p>All payments will be retagged.</p>")
        link = result.rows["ObjectUpdateMessage"][0]
        self.assertEqual(link["ObjectMessageID"], om["ObjectMessageID"])
        self.assertEqual(link["ObjectUpdateMessageIsVisible"], 1)
        edges = {
            (e["TableName"], e["ChildTableName"], e["ChildTableRowID"]) for e in result.edges
        }
        self.assertIn(("Object", "ObjectMessage", om["ObjectMessageID"]), edges)
        self.assertIn(
            ("ObjectUpdateAction", "ObjectUpdateMessage", link["ObjectUpdateMessageID"]),
            edges,
        )
        lt = {
            (r["TableName"], r["ColumnName"], r["UserLanguageCode"]): r
            for r in result.rows["LanguageTable"]
        }
        self.assertEqual(
            lt[("ObjectMessage", "ObjectMessageName", "cs")]["LanguageTableData"],
            "Přestítkovat platby",
        )
        self.assertEqual(
            lt[("ObjectMessage", "ObjectMessageFormat", "cs")]["LanguageTableData"],
            "<p>Přestítkují se všechny platby.</p>",
        )

    def test_roundtrip_extract(self) -> None:
        spec = _base_spec()
        spec["objectMessages"] = [
            {
                "key": "retag_payments",
                "name": "Retag payments",
                "style": "warning",
                "order": 10,
                "html": "<p>All payments will be retagged.</p>",
                "conditions": [{"field": "NAME", "type": "is_not_empty"}],
            }
        ]
        spec["updateActions"] = [
            {
                "key": "update",
                "name": "Update",
                "order": 10,
                "messages": [{"key": "retag_payments", "visible": True}],
            }
        ]
        spec["languageTable"] = {
            "objectMessages": {
                "retag_payments": {
                    "cs": "Přestítkovat platby",
                    "html": {"cs": "<p>CS html</p>"},
                }
            }
        }
        result = build_rows(spec)
        xml_bytes = build_object_transfer_xml(
            result.rows, dedupe_edges(result.edges), build_object_map(dedupe_edges(result.edges))
        )
        with tempfile.TemporaryDirectory() as tmp:
            xml_path = Path(tmp) / "ot.xml"
            xml_path.write_bytes(xml_bytes)
            extracted = extract_spec(xml_path)

        messages = extracted["objectMessages"]
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["key"], "retag_payments")
        self.assertEqual(messages[0]["style"], "warning")
        self.assertEqual(messages[0]["html"], "<p>All payments will be retagged.</p>")
        self.assertEqual(
            messages[0]["conditions"],
            [{"field": "NAME", "type": "is_not_empty"}],
        )
        self.assertEqual(
            extracted["updateActions"][0]["messages"],
            [{"key": "retag_payments", "visible": True}],
        )
        lt = extracted["languageTable"]["objectMessages"]["retag_payments"]
        self.assertEqual(lt["cs"], "Přestítkovat platby")
        self.assertEqual(lt["html"]["cs"], "<p>CS html</p>")


if __name__ == "__main__":
    unittest.main()
