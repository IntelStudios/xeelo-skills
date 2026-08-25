"""Regression tests for ot_builder ID allocation."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ot_builder.ids import IdRegistry, build_registry  # noqa: E402
from ot_builder.parse import TransferIndex, collect_table_max_ids  # noqa: E402


class IdRegistryTests(unittest.TestCase):
    def test_require_returns_same_id_for_same_key(self) -> None:
        registry = IdRegistry({"ids": {"base": 9000}})
        self.assertEqual(registry.require("fields", "line_castka"), 9001)
        self.assertEqual(registry.require("fields", "line_castka"), 9001)
        self.assertEqual(registry.require("roles", "requestor"), 9001)
        self.assertEqual(registry.require("roles", "requestor"), 9001)

    def test_require_scalar_returns_same_id(self) -> None:
        registry = IdRegistry({"ids": {"base": 9000}})
        self.assertEqual(registry.require_scalar("workflowId"), 9001)
        self.assertEqual(registry.require_scalar("workflowId"), 9001)

    def test_build_registry_skips_uuid_explicit_values(self) -> None:
        registry = build_registry(
            {
                "ids": {
                    "base": 9100,
                    "explicit": {
                        "objectId": 9100,
                        "objectDefaultExternalLink": "A309AFD4-0102-463C-A6F1-8EE272DAB6F2",
                        "objectDefaultExternalLinks": {
                            "cash_register": "A309AFD4-0102-463C-A6F1-8EE272DAB6F2"
                        },
                    },
                }
            }
        )
        self.assertEqual(registry.require_scalar("objectId"), 9100)

    def test_by_table_allocates_per_table(self) -> None:
        registry = build_registry(
            {
                "ids": {
                    "byTable": {
                        "ObjectLine": {"9107": 9107, "9112": 9112},
                        "ObjectDefaultLine": {"4": 4, "15": 15},
                    }
                }
            }
        )
        self.assertEqual(registry.require("fields", "new_field"), 9113)
        self.assertEqual(registry.require("objectDefaultLines", "new_line"), 16)

    def test_base_map_overrides_by_table_max(self) -> None:
        registry = build_registry(
            {
                "ids": {
                    "base": {"ObjectLine": 9200},
                    "byTable": {"ObjectLine": {"9107": 9107, "9112": 9112}},
                }
            }
        )
        self.assertEqual(registry.require("fields", "new_field"), 9201)

    def test_legacy_integer_base_without_by_table(self) -> None:
        registry = IdRegistry({"ids": {"base": 9100}})
        self.assertEqual(registry.require("fields", "a"), 9101)
        self.assertEqual(registry.require("objectActions", "b"), 9101)


class CollectTableMaxIdsTests(unittest.TestCase):
    def test_max_per_table_sorted_keys(self) -> None:
        index = TransferIndex(edges=[], rows={
            "ObjectLine": [{"ObjectLineID": 9107}, {"ObjectLineID": 9112}],
            "ObjectAction": [{"ObjectActionID": 9132}],
        }, transfer_info={})
        self.assertEqual(
            collect_table_max_ids(index),
            {"ObjectAction": 9132, "ObjectLine": 9112},
        )


if __name__ == "__main__":
    unittest.main()
