"""object.directCreate: ObjectIsDirectCreate."""

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


def _base_spec() -> dict:
    return {
        "version": 2,
        "kind": "create_object",
        "object": {
            "name": "Txn",
            "code": "TXN",
            "objectType": "Finance",
            "directCreate": True,
        },
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
        "ids": {"base": 9300},
    }


class DirectCreateGenerateTests(unittest.TestCase):
    def test_emits_when_true(self) -> None:
        result = build_rows(_base_spec())
        obj = result.rows["Object"][0]
        self.assertEqual(obj["ObjectIsDirectCreate"], 1)

    def test_emits_zero_when_false(self) -> None:
        spec = _base_spec()
        spec["object"]["directCreate"] = False
        result = build_rows(spec)
        obj = result.rows["Object"][0]
        self.assertEqual(obj["ObjectIsDirectCreate"], 0)

    def test_omits_when_unset(self) -> None:
        spec = _base_spec()
        del spec["object"]["directCreate"]
        result = build_rows(spec)
        obj = result.rows["Object"][0]
        self.assertNotIn("ObjectIsDirectCreate", obj)


class DirectCreateRoundtripTests(unittest.TestCase):
    def test_extract_emits_true(self) -> None:
        spec = _base_spec()
        result = build_rows(spec)
        xml_bytes = build_object_transfer_xml(
            result.rows, dedupe_edges(result.edges), build_object_map(dedupe_edges(result.edges))
        )
        with tempfile.TemporaryDirectory() as tmp:
            xml_path = Path(tmp) / "ot.xml"
            xml_path.write_bytes(xml_bytes)
            extracted = extract_spec(xml_path)

        self.assertTrue(extracted["object"]["directCreate"])

    def test_extract_omits_false(self) -> None:
        spec = _base_spec()
        spec["object"]["directCreate"] = False
        result = build_rows(spec)
        xml_bytes = build_object_transfer_xml(
            result.rows, dedupe_edges(result.edges), build_object_map(dedupe_edges(result.edges))
        )
        with tempfile.TemporaryDirectory() as tmp:
            xml_path = Path(tmp) / "ot.xml"
            xml_path.write_bytes(xml_bytes)
            extracted = extract_spec(xml_path)

        self.assertNotIn("directCreate", extracted["object"])


if __name__ == "__main__":
    unittest.main()
