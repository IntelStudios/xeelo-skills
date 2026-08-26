"""Canonical YAML key order for xeelo-spec (OT extract insertion order)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ot_builder.spec_key_order import (  # noqa: E402
    FIELD_KEYS,
    ordered_mapping,
    reorder_field,
    reorder_spec,
)
from ot_builder.spec_loader import load_spec, write_spec  # noqa: E402


def _base_spec(**overrides) -> dict:
    spec = {
        "version": 2,
        "kind": "create_object",
        "object": {"name": "Account", "code": "ACCOUNT", "objectType": "Finance"},
        "company": {"name": "KB"},
        "layout": {
            "tabs": [
                {
                    "name": "General",
                    "placement": 0,
                    "order": 1,
                    "sections": [
                        {
                            "name": "Details",
                            "order": 1,
                            "width": 100,
                            "fields": [
                                {
                                    "name": "Account Number",
                                    "code": "ACCOUNT_NUMBER",
                                    "type": "text",
                                    "slot": 1,
                                    "width": 50,
                                    "order": 1,
                                    "mandatory": True,
                                }
                            ],
                        }
                    ],
                }
            ]
        },
    }
    spec.update(overrides)
    return spec


class OrderedMappingTests(unittest.TestCase):
    def test_known_keys_first_unknown_last(self) -> None:
        data = {"slot": 1, "name": "N", "extra": True, "code": "C"}
        out = ordered_mapping(data, ("name", "code", "type", "width", "order", "slot"))
        self.assertEqual(list(out.keys()), ["name", "code", "slot", "extra"])
        self.assertEqual(out["extra"], True)
        self.assertEqual(out["slot"], 1)


class ReorderFieldTests(unittest.TestCase):
    def test_slot_after_width_and_order(self) -> None:
        field = {
            "name": "Title",
            "code": "TITLE",
            "type": "text",
            "slot": 1,
            "width": 50,
            "order": 2,
            "mandatory": True,
        }
        out = reorder_field(field)
        self.assertEqual(
            list(out.keys()),
            ["name", "code", "type", "width", "order", "slot", "mandatory"],
        )
        self.assertEqual(list(FIELD_KEYS)[:6], ["name", "code", "type", "width", "order", "slot"])

    def test_values_unchanged(self) -> None:
        field = {"name": "Qty", "code": "QTY", "type": "number", "precision": 2, "width": 25, "order": 3}
        out = reorder_field(field)
        self.assertEqual(out["precision"], 2)
        self.assertEqual(out["width"], 25)
        self.assertEqual(list(out.keys()), ["name", "code", "type", "width", "order", "precision"])


class ReorderSpecTests(unittest.TestCase):
    def setUp(self) -> None:
        if yaml is None:
            self.skipTest("PyYAML not installed")

    def test_tab_alwayshidden_after_sections(self) -> None:
        spec = _base_spec()
        spec["layout"]["tabs"][0]["alwaysHidden"] = True
        # put alwaysHidden first like schema/docs used to
        tab = spec["layout"]["tabs"][0]
        spec["layout"]["tabs"][0] = {
            "alwaysHidden": True,
            "name": tab["name"],
            "placement": tab["placement"],
            "order": tab["order"],
            "sections": tab["sections"],
        }
        out = reorder_spec(spec)
        self.assertEqual(
            list(out["layout"]["tabs"][0].keys()),
            ["name", "placement", "order", "sections", "alwaysHidden"],
        )

    def test_object_icon_before_request_title(self) -> None:
        spec = _base_spec()
        spec["object"] = {
            "name": "Account",
            "requestTitleField": "TITLE",
            "code": "ACCOUNT",
            "icon": "fa-university fa-solid fa-fw",
            "objectType": "Finance",
            "color": "blue",
        }
        out = reorder_spec(spec)
        self.assertEqual(
            list(out["object"].keys()),
            ["name", "code", "objectType", "icon", "color", "requestTitleField"],
        )

    def test_write_spec_roundtrip_field_order(self) -> None:
        spec = _base_spec()
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "obj"
            write_spec(spec, directory)
            text = (directory / "spec" / "object.yaml").read_text(encoding="utf-8")
            dumped = yaml.safe_load(text)
            field = dumped["layout"]["tabs"][0]["sections"][0]["fields"][0]
            self.assertEqual(
                list(field.keys()),
                ["name", "code", "type", "width", "order", "slot", "mandatory"],
            )
            loaded = load_spec(directory)
        self.assertEqual(loaded["layout"]["tabs"][0]["sections"][0]["fields"][0]["slot"], 1)
        self.assertEqual(loaded["object"]["name"], "Account")


if __name__ == "__main__":
    unittest.main()
