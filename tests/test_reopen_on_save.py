"""Generate/extract roundtrip for templates[].reopenOnSave and updateActions[].reopenOnSave."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ot_builder.extract import extract_spec  # noqa: E402
from ot_builder.hierarchy import build_object_map, dedupe_edges  # noqa: E402
from ot_builder.reopen import reopen_on_save_id  # noqa: E402
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
        "templates": [
            {
                "key": "default",
                "name": "Default",
                "isDefault": True,
            }
        ],
        "ids": {"base": 9400},
    }


def _roundtrip(spec: dict) -> dict:
    result = build_rows(spec)
    xml_bytes = build_object_transfer_xml(
        result.rows, dedupe_edges(result.edges), build_object_map(dedupe_edges(result.edges))
    )
    with tempfile.TemporaryDirectory() as tmp:
        xml_path = Path(tmp) / "ot.xml"
        xml_path.write_bytes(xml_bytes)
        return extract_spec(xml_path)


class ReopenHelperTests(unittest.TestCase):
    def test_slug_mapping(self) -> None:
        self.assertIsNone(reopen_on_save_id(None))
        self.assertIsNone(reopen_on_save_id("none"))
        self.assertIsNone(reopen_on_save_id("close"))
        self.assertEqual(reopen_on_save_id("open-only-everytime"), 1)
        self.assertEqual(reopen_on_save_id("open-with-actions"), 2)
        self.assertEqual(reopen_on_save_id("open-only-assigned"), 3)

    def test_unknown_slug_raises(self) -> None:
        with self.assertRaises(ValueError):
            reopen_on_save_id("owner")


class TemplateReopenOnSaveTests(unittest.TestCase):
    def test_omit_does_not_emit_column(self) -> None:
        result = build_rows(_base_spec())
        row = result.rows["ObjectDefault"][0]
        self.assertNotIn("ObjectDefaultReopenTypeID", row)

    def test_none_does_not_emit_column(self) -> None:
        spec = _base_spec()
        spec["templates"][0]["reopenOnSave"] = "none"
        result = build_rows(spec)
        self.assertNotIn("ObjectDefaultReopenTypeID", result.rows["ObjectDefault"][0])

    def test_generate_and_extract_open_only_assigned(self) -> None:
        spec = _base_spec()
        spec["templates"][0]["reopenOnSave"] = "open-only-assigned"
        result = build_rows(spec)
        self.assertEqual(result.rows["ObjectDefault"][0]["ObjectDefaultReopenTypeID"], 3)
        extracted = _roundtrip(spec)
        self.assertEqual(extracted["templates"][0]["reopenOnSave"], "open-only-assigned")

    def test_extract_omits_templates_when_reopen_unset(self) -> None:
        extracted = _roundtrip(_base_spec())
        self.assertNotIn("templates", extracted)


class UpdateActionReopenOnSaveTests(unittest.TestCase):
    def test_generate_and_extract(self) -> None:
        spec = _base_spec()
        spec["updateActions"] = [
            {
                "key": "amend",
                "name": "Amend",
                "order": 10,
                "reopenOnSave": "open-with-actions",
            }
        ]
        result = build_rows(spec)
        self.assertEqual(
            result.rows["ObjectUpdateAction"][0]["ObjectUpdateActionReopenTypeID"], 2
        )
        extracted = _roundtrip(spec)
        self.assertEqual(extracted["updateActions"][0]["reopenOnSave"], "open-with-actions")

    def test_omit_does_not_emit_column(self) -> None:
        spec = _base_spec()
        spec["updateActions"] = [{"key": "amend", "name": "Amend", "order": 10}]
        result = build_rows(spec)
        self.assertNotIn(
            "ObjectUpdateActionReopenTypeID", result.rows["ObjectUpdateAction"][0]
        )
