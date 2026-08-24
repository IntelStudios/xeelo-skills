"""Tests for TableComments generate/extract."""

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
from ot_builder.jsonout import build_object_transfer_json  # noqa: E402
from ot_builder.rows import build_rows  # noqa: E402
from ot_builder.spec_loader import write_spec  # noqa: E402
from ot_builder.xml import build_object_transfer_xml  # noqa: E402


def _spec() -> dict:
    return {
        "version": 2,
        "kind": "create_object",
        "object": {"name": "Account", "code": "ACCOUNT", "objectType": "Finance"},
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
                                    "name": "Type",
                                    "code": "TYPE",
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
        "periodics": [
            {
                "key": "load_fio_hourly",
                "name": "Load FIO transactions",
                "requestType": "completed",
                "actions": [
                    {
                        "key": "start_load",
                        "name": "Start load",
                        "typeCode": "spEndPointRunNodeJSMain",
                        "order": 10,
                        "params": {"CustomJS": 'export async function main() { return "OK"; }'},
                    }
                ],
            }
        ],
        "comments": {
            "object": [
                {
                    "html": "<p>FIO accounts that drive payment import.</p>",
                    "userName": "xeelo-skills",
                    "date": "2026-08-24T12:00:00",
                }
            ],
            "lines": {
                "TYPE": [
                    {
                        "html": "<p>Payment source. Hourly periodic matches FIO.</p>",
                        "date": "2026-08-24T12:01:00",
                    }
                ]
            },
            "periodics": {
                "load_fio_hourly": [
                    {
                        "html": "<p>2026-08-24: hourly scheduler → load_transactions.</p>",
                        "date": "2026-08-24T12:02:00",
                    }
                ]
            },
        },
        "ids": {"base": 9100},
    }


class CommentGenerateTests(unittest.TestCase):
    def test_emits_table_comments_and_json(self) -> None:
        result = build_rows(_spec())
        rows = result.rows["TableComments"]
        self.assertEqual(len(rows), 3)
        by_parent = {(r["TableName"], r["TableRowID"]): r for r in rows}
        object_id = result.rows["Object"][0]["ObjectID"]
        type_id = next(
            r["ObjectLineID"] for r in result.rows["ObjectLine"] if r["ObjectLineCode"] == "TYPE"
        )
        periodic_id = result.rows["Periodic"][0]["PeriodicID"]
        self.assertEqual(
            by_parent[("Object", object_id)]["TableCommentData"],
            "<p>FIO accounts that drive payment import.</p>",
        )
        self.assertEqual(by_parent[("Object", object_id)]["UserID"], 0)
        self.assertEqual(by_parent[("Object", object_id)]["UserName"], "xeelo-skills")
        self.assertEqual(by_parent[("ObjectLine", type_id)]["TableCommentDate"], "2026-08-24T12:01:00")
        self.assertIn("hourly scheduler", by_parent[("Periodic", periodic_id)]["TableCommentData"])
        self.assertTrue(
            any(
                e["ChildTableName"] == "TableComments" and e["TableName"] == "ObjectLine"
                for e in result.edges
            )
        )

        text, _omitted = build_object_transfer_json(result.rows)
        payload = json.loads(text)
        self.assertIn("TableComments", payload)
        self.assertEqual(len(payload["TableComments"]), 3)
        self.assertNotIn("AttachmentID", payload["TableComments"][0])

    def test_unknown_line_raises(self) -> None:
        spec = _spec()
        spec["comments"]["lines"]["MISSING"] = [{"html": "<p>nope</p>"}]
        with self.assertRaises(ValueError) as ctx:
            build_rows(spec)
        self.assertIn("MISSING", str(ctx.exception))

    def test_write_spec_fragment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            entry = write_spec(_spec(), Path(tmp) / "obj")
            comments_path = Path(tmp) / "obj" / "spec" / "comments.yaml"
            self.assertTrue(comments_path.is_file())
            text = comments_path.read_text(encoding="utf-8")
            self.assertIn("comments:", text)
            self.assertIn("TYPE:", text)
            includes = entry.read_text(encoding="utf-8")
            self.assertIn("spec/comments.yaml", includes)

    def test_xml_roundtrip_extract(self) -> None:
        spec = _spec()
        result = build_rows(spec)
        xml_bytes = build_object_transfer_xml(
            result.rows, dedupe_edges(result.edges), build_object_map(dedupe_edges(result.edges))
        )
        with tempfile.TemporaryDirectory() as tmp:
            xml_path = Path(tmp) / "ot.xml"
            xml_path.write_bytes(xml_bytes)
            extracted = extract_spec(xml_path)

        self.assertEqual(
            extracted["comments"]["object"][0]["html"],
            "<p>FIO accounts that drive payment import.</p>",
        )
        self.assertEqual(
            extracted["comments"]["lines"]["TYPE"][0]["html"],
            "<p>Payment source. Hourly periodic matches FIO.</p>",
        )
        periodic_key = next(iter(extracted["comments"]["periodics"]))
        self.assertIn("hourly scheduler", extracted["comments"]["periodics"][periodic_key][0]["html"])
        explicit = extracted["ids"]["explicit"]
        self.assertIn("tableComments", explicit)
        self.assertTrue(any(k.startswith("ObjectLine:TYPE:") for k in explicit["tableComments"]))


if __name__ == "__main__":
    unittest.main()
