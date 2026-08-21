"""onGrid layouts: distinct ObjectLineOnGrid IDs per size × type × module × field."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ot_builder.extract import _build_ongrid  # noqa: E402
from ot_builder.ongrid import layout_id_key, require_ongrid_id  # noqa: E402
from ot_builder.ids import IdRegistry  # noqa: E402
from ot_builder.parse import TransferIndex  # noqa: E402
from ot_builder.rows import build_rows  # noqa: E402


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
                                    "name": "Amount",
                                    "code": "amount",
                                    "type": "number",
                                    "slot": 1,
                                    "width": 50,
                                    "order": 10,
                                    "precision": 2,
                                },
                                {
                                    "name": "Invoice",
                                    "code": "invoice",
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
        "onGrid": {
            "fields": {
                "amount": {"allowed": True},
                "invoice": {"allowed": True},
            },
            "layouts": [
                {
                    "size": "Large",
                    "type": "Grid",
                    "module": "Items",
                    "placements": [
                        {
                            "row": "A",
                            "columns": [
                                {"field": "amount", "position": 0, "length": 80},
                                {"field": "invoice", "position": 80, "length": 20},
                            ],
                        }
                    ],
                },
                {
                    "size": "Small",
                    "type": "Grid",
                    "module": "Items",
                    "placements": [
                        {
                            "row": "A",
                            "columns": [{"field": "amount", "position": 0, "length": 100}],
                        }
                    ],
                },
            ],
        },
        "ids": {"base": 9100},
    }


class OnGridIdKeyTests(unittest.TestCase):
    def test_layout_id_key(self) -> None:
        self.assertEqual(
            layout_id_key("Large", "Grid", "Items", "amount"),
            "Large/Grid/Items/amount",
        )

    def test_legacy_field_code_used_once(self) -> None:
        registry = IdRegistry(
            {"ids": {"explicit": {"objectLineOnGrid": {"amount": 9148}}}}
        )
        used: set[str] = set()
        first = require_ongrid_id(
            registry,
            size="Large",
            grid_type="Grid",
            module="Items",
            field_code="amount",
            used_legacy=used,
        )
        second = require_ongrid_id(
            registry,
            size="Small",
            grid_type="Grid",
            module="Items",
            field_code="amount",
            used_legacy=used,
        )
        self.assertEqual(first, 9148)
        self.assertNotEqual(second, first)


class OnGridGenerateTests(unittest.TestCase):
    def test_same_field_two_sizes_distinct_ids(self) -> None:
        result = build_rows(_base_spec())
        rows = result.rows["ObjectLineOnGrid"]
        self.assertEqual(len(rows), 3)
        ids = {row["ObjectLineOnGridID"] for row in rows}
        self.assertEqual(len(ids), 3)
        amount_ids = {
            r["ObjectLineOnGridSize"]: r["ObjectLineOnGridID"]
            for r in rows
            if r["ObjectLineOnGridPosition"] == 0
        }
        self.assertIn("Large", amount_ids)
        self.assertIn("Small", amount_ids)
        self.assertNotEqual(amount_ids["Large"], amount_ids["Small"])


class OnGridExtractTests(unittest.TestCase):
    def test_extract_composite_keys(self) -> None:
        index = TransferIndex(
            edges=[],
            rows={
                "ObjectLine": [
                    {
                        "ObjectLineID": 1,
                        "ObjectID": 9,
                        "ObjectLineCode": "amount",
                        "ObjectLineOnGridIsAllowed": 1,
                    }
                ],
                "ObjectLineOnGrid": [
                    {
                        "ObjectLineOnGridID": 100,
                        "ObjectID": 9,
                        "ObjectLineID": 1,
                        "ObjectLineOnGridSize": "Large",
                        "ObjectLineOnGridType": "Grid",
                        "ObjectLineOnGridModule": "Items",
                        "ObjectLineOnGridRow": "A",
                        "ObjectLineOnGridPosition": 0,
                        "ObjectLineOnGridLength": 100,
                    },
                    {
                        "ObjectLineOnGridID": 101,
                        "ObjectID": 9,
                        "ObjectLineID": 1,
                        "ObjectLineOnGridSize": "Small",
                        "ObjectLineOnGridType": "Grid",
                        "ObjectLineOnGridModule": "Items",
                        "ObjectLineOnGridRow": "A",
                        "ObjectLineOnGridPosition": 0,
                        "ObjectLineOnGridLength": 100,
                    },
                ],
            },
            transfer_info={},
        )
        ongrid, explicit = _build_ongrid(index, 9, {1: "amount"})
        self.assertEqual(
            explicit,
            {
                "Large/Grid/Items/amount": 100,
                "Small/Grid/Items/amount": 101,
            },
        )
        sizes = {layout["size"] for layout in ongrid["layouts"]}
        self.assertEqual(sizes, {"Large", "Small"})

    def test_extract_tag_only_without_allowed(self) -> None:
        index = TransferIndex(
            edges=[],
            rows={
                "ObjectLine": [
                    {
                        "ObjectLineID": 1,
                        "ObjectID": 9,
                        "ObjectLineCode": "amount",
                        "ObjectLineOnGridIsAllowed": 1,
                    },
                    {
                        "ObjectLineID": 2,
                        "ObjectID": 9,
                        "ObjectLineCode": "label_tag",
                        "ObjectLineOnGridIsAllowed": 0,
                        "ObjectLineOnGridIsTag": 1,
                    },
                ],
                "ObjectLineOnGrid": [
                    {
                        "ObjectLineOnGridID": 100,
                        "ObjectID": 9,
                        "ObjectLineID": 1,
                        "ObjectLineOnGridSize": "Large",
                        "ObjectLineOnGridType": "Grid",
                        "ObjectLineOnGridModule": "Items",
                        "ObjectLineOnGridRow": "A",
                        "ObjectLineOnGridPosition": 0,
                        "ObjectLineOnGridLength": 100,
                    },
                    {
                        "ObjectLineOnGridID": 101,
                        "ObjectID": 9,
                        "ObjectLineID": 2,
                        "ObjectLineOnGridSize": "Large",
                        "ObjectLineOnGridType": "Grid",
                        "ObjectLineOnGridModule": "Items",
                        "ObjectLineOnGridRow": "B",
                        "ObjectLineOnGridPosition": 0,
                        "ObjectLineOnGridLength": 50,
                    },
                ],
            },
            transfer_info={},
        )
        ongrid, explicit = _build_ongrid(
            index, 9, {1: "amount", 2: "label_tag"}
        )
        self.assertEqual(
            ongrid["fields"]["label_tag"],
            {"allowed": False, "isTag": True},
        )
        self.assertNotIn("Large/Grid/Items/label_tag", explicit)
        fields_in_layout = {
            col["field"]
            for layout in ongrid["layouts"]
            for place in layout["placements"]
            for col in place["columns"]
        }
        self.assertIn("amount", fields_in_layout)
        self.assertNotIn("label_tag", fields_in_layout)

    def test_extract_is_total_without_allowed(self) -> None:
        index = TransferIndex(
            edges=[],
            rows={
                "ObjectLine": [
                    {
                        "ObjectLineID": 1,
                        "ObjectID": 9,
                        "ObjectLineCode": "amount",
                        "ObjectLineOnGridIsAllowed": 1,
                        "ObjectLineOnGridIsTotal": 1,
                    },
                    {
                        "ObjectLineID": 2,
                        "ObjectID": 9,
                        "ObjectLineCode": "income",
                        "ObjectLineOnGridIsAllowed": 0,
                        "ObjectLineOnGridIsTotal": 1,
                    },
                ],
                "ObjectLineOnGrid": [],
            },
            transfer_info={},
        )
        ongrid, _explicit = _build_ongrid(
            index, 9, {1: "amount", 2: "income"}
        )
        self.assertEqual(
            ongrid["fields"]["amount"],
            {"allowed": True, "isTotal": True},
        )
        self.assertEqual(
            ongrid["fields"]["income"],
            {"allowed": False, "isTotal": True},
        )


class OnGridTotalGenerateTests(unittest.TestCase):
    def test_emits_is_total(self) -> None:
        spec = _base_spec()
        spec["onGrid"]["fields"]["amount"]["isTotal"] = True
        spec["onGrid"]["fields"]["income"] = {
            "allowed": False,
            "isTotal": True,
        }
        spec["layout"]["tabs"][0]["sections"][0]["fields"].append(
            {
                "name": "Income",
                "code": "income",
                "type": "number",
                "slot": 3,
                "width": 50,
                "order": 30,
                "precision": 2,
            }
        )
        result = build_rows(spec)
        by_code = {r["ObjectLineCode"]: r for r in result.rows["ObjectLine"]}
        self.assertEqual(by_code["amount"]["ObjectLineOnGridIsTotal"], 1)
        self.assertEqual(by_code["income"]["ObjectLineOnGridIsAllowed"], 0)
        self.assertEqual(by_code["income"]["ObjectLineOnGridIsTotal"], 1)
        self.assertNotIn("ObjectLineOnGridIsTotal", by_code["invoice"])


if __name__ == "__main__":
    unittest.main()
