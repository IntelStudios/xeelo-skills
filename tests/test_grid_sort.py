"""object.gridSort: ObjectGridSortObjectLineID + ObjectGridSortType."""

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
            "gridSort": {"field": "DATE", "type": "DESC"},
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
                                    "name": "Date",
                                    "code": "DATE",
                                    "type": "date",
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


class GridSortGenerateTests(unittest.TestCase):
    def test_emits_sort_columns(self) -> None:
        result = build_rows(_base_spec())
        obj = result.rows["Object"][0]
        date_id = result.rows["ObjectLine"][0]["ObjectLineID"]
        self.assertEqual(obj["ObjectGridSortObjectLineID"], date_id)
        self.assertEqual(obj["ObjectGridSortType"], "DESC")

    def test_omits_when_unset(self) -> None:
        spec = _base_spec()
        del spec["object"]["gridSort"]
        result = build_rows(spec)
        obj = result.rows["Object"][0]
        self.assertNotIn("ObjectGridSortObjectLineID", obj)
        self.assertNotIn("ObjectGridSortType", obj)

    def test_rejects_invalid_type(self) -> None:
        spec = _base_spec()
        spec["object"]["gridSort"]["type"] = "None"
        with self.assertRaises(ValueError):
            build_rows(spec)


class GridSortRoundtripTests(unittest.TestCase):
    def test_extract_rebuilds_grid_sort(self) -> None:
        spec = _base_spec()
        result = build_rows(spec)
        xml_bytes = build_object_transfer_xml(
            result.rows, dedupe_edges(result.edges), build_object_map(dedupe_edges(result.edges))
        )
        with tempfile.TemporaryDirectory() as tmp:
            xml_path = Path(tmp) / "ot.xml"
            xml_path.write_bytes(xml_bytes)
            extracted = extract_spec(xml_path)

        self.assertEqual(
            extracted["object"]["gridSort"],
            {"field": "DATE", "type": "DESC"},
        )


if __name__ == "__main__":
    unittest.main()
