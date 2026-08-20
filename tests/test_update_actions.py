"""Tests for ObjectUpdateAccess and ObjectDefaultAccess visible/editable flags."""

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
from ot_builder.update_actions import (  # noqa: E402
    resolve_access_flags,
    template_access_differs_from_default,
)
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
                                },
                                {
                                    "name": "Secret",
                                    "code": "SECRET",
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


class AccessFlagHelperTests(unittest.TestCase):
    def test_editable_implies_visible(self) -> None:
        self.assertEqual(resolve_access_flags({"editable": True, "visible": False}), (1, 1))
        self.assertEqual(resolve_access_flags({"editable": True}), (1, 1))

    def test_hide_and_lock(self) -> None:
        self.assertEqual(resolve_access_flags({"visible": False}), (0, 0))
        self.assertEqual(resolve_access_flags({"editable": False}), (0, 1))
        self.assertEqual(resolve_access_flags({}), (0, 1))

    def test_template_refresh_default_omitted(self) -> None:
        self.assertFalse(
            template_access_differs_from_default(
                {"ObjectLineIsEditableCreate": 1, "ObjectLineIsVisibleCreate": 1}
            )
        )
        self.assertTrue(
            template_access_differs_from_default(
                {"ObjectLineIsEditableCreate": 0, "ObjectLineIsVisibleCreate": 1}
            )
        )
        self.assertTrue(
            template_access_differs_from_default(
                {"ObjectLineIsEditableCreate": 1, "ObjectLineIsVisibleCreate": 0}
            )
        )


class UpdateAccessGenerateTests(unittest.TestCase):
    def test_emits_editable_visible_bits(self) -> None:
        spec = _base_spec()
        spec["updateActions"] = [
            {
                "key": "amend",
                "name": "Amend",
                "order": 10,
                "access": [
                    {"field": "NAME", "editable": True, "visible": True},
                    {"field": "SECRET", "visible": False},
                ],
            }
        ]
        result = build_rows(spec)
        rows = result.rows["ObjectUpdateAccess"]
        self.assertEqual(len(rows), 2)
        by_line = {row["ObjectLineID"]: row for row in rows}
        name_id = next(r["ObjectLineID"] for r in result.rows["ObjectLine"] if r["ObjectLineCode"] == "NAME")
        secret_id = next(
            r["ObjectLineID"] for r in result.rows["ObjectLine"] if r["ObjectLineCode"] == "SECRET"
        )
        self.assertEqual(by_line[name_id]["ObjectLineIsEditableUpdate"], 1)
        self.assertEqual(by_line[name_id]["ObjectLineIsVisibleUpdate"], 1)
        self.assertEqual(by_line[secret_id]["ObjectLineIsEditableUpdate"], 0)
        self.assertEqual(by_line[secret_id]["ObjectLineIsVisibleUpdate"], 0)
        edges = {
            (e["TableName"], e["ChildTableName"], e["ChildTableRowID"]) for e in result.edges
        }
        action_id = result.rows["ObjectUpdateAction"][0]["ObjectUpdateActionID"]
        self.assertIn(("Object", "ObjectUpdateAction", action_id), edges)
        for row in rows:
            self.assertIn(
                ("ObjectUpdateAction", "ObjectUpdateAccess", row["ObjectUpdateAccessID"]),
                edges,
            )

    def test_omits_access_table_when_empty(self) -> None:
        spec = _base_spec()
        spec["updateActions"] = [{"key": "amend", "name": "Amend", "order": 10}]
        result = build_rows(spec)
        self.assertNotIn("ObjectUpdateAccess", result.rows)

    def test_roundtrip_extract_omits_refresh_defaults(self) -> None:
        spec = _base_spec()
        spec["updateActions"] = [
            {
                "key": "amend",
                "name": "Amend",
                "order": 10,
                "access": [
                    {"field": "NAME", "editable": True, "visible": True},
                    {"field": "SECRET", "editable": False, "visible": True},
                ],
            }
        ]
        result = build_rows(spec)
        xml_bytes = build_object_transfer_xml(
            result.rows, dedupe_edges(result.edges), build_object_map(dedupe_edges(result.edges))
        )
        with tempfile.TemporaryDirectory() as tmp:
            xml_path = Path(tmp) / "ot.xml"
            xml_path.write_bytes(xml_bytes)
            extracted = extract_spec(xml_path)

        actions = extracted["updateActions"]
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["key"], "amend")
        self.assertEqual(
            actions[0]["access"],
            [{"field": "NAME", "editable": True, "visible": True}],
        )
        self.assertIn("amend/NAME", extracted["ids"]["explicit"]["objectUpdateAccess"])
        self.assertNotIn("amend/SECRET", extracted["ids"]["explicit"].get("objectUpdateAccess", {}))


class TemplateAccessGenerateTests(unittest.TestCase):
    def test_emits_create_access_exceptions(self) -> None:
        spec = _base_spec()
        spec["templates"] = [
            {
                "key": "default",
                "name": "Default",
                "isDefault": True,
                "access": [
                    {"field": "SECRET", "visible": False},
                    {"field": "NAME", "editable": False},
                ],
            }
        ]
        result = build_rows(spec)
        rows = result.rows["ObjectDefaultAccess"]
        self.assertEqual(len(rows), 2)
        by_line = {row["ObjectLineID"]: row for row in rows}
        name_id = next(r["ObjectLineID"] for r in result.rows["ObjectLine"] if r["ObjectLineCode"] == "NAME")
        secret_id = next(
            r["ObjectLineID"] for r in result.rows["ObjectLine"] if r["ObjectLineCode"] == "SECRET"
        )
        self.assertEqual(by_line[secret_id]["ObjectLineIsVisibleCreate"], 0)
        self.assertEqual(by_line[secret_id]["ObjectLineIsEditableCreate"], 0)
        self.assertEqual(by_line[name_id]["ObjectLineIsEditableCreate"], 0)
        self.assertEqual(by_line[name_id]["ObjectLineIsVisibleCreate"], 1)
        edges = {
            (e["TableName"], e["ChildTableName"], e["ChildTableRowID"]) for e in result.edges
        }
        for row in rows:
            self.assertIn(
                ("ObjectDefault", "ObjectDefaultAccess", row["ObjectDefaultAccessID"]),
                edges,
            )

    def test_does_not_emit_default_create_access(self) -> None:
        result = build_rows(_base_spec())
        self.assertNotIn("ObjectDefaultAccess", result.rows)

    def test_roundtrip_extract_omits_create_refresh_defaults(self) -> None:
        spec = _base_spec()
        spec["templates"] = [
            {
                "key": "default",
                "name": "Default",
                "isDefault": True,
                "access": [
                    {"field": "SECRET", "visible": False},
                    {"field": "NAME", "editable": True, "visible": True},
                ],
            }
        ]
        result = build_rows(spec)
        xml_bytes = build_object_transfer_xml(
            result.rows, dedupe_edges(result.edges), build_object_map(dedupe_edges(result.edges))
        )
        with tempfile.TemporaryDirectory() as tmp:
            xml_path = Path(tmp) / "ot.xml"
            xml_path.write_bytes(xml_bytes)
            extracted = extract_spec(xml_path)

        templates = extracted["templates"]
        self.assertEqual(len(templates), 1)
        access = templates[0]["access"]
        self.assertEqual(
            access,
            [{"field": "SECRET", "editable": False, "visible": False}],
        )
        explicit = extracted["ids"]["explicit"]["objectDefaultAccess"]
        self.assertIn("SECRET", explicit)
        self.assertNotIn("NAME", explicit)


if __name__ == "__main__":
    unittest.main()
