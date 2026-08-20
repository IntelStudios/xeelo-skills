"""Offline Font Awesome catalog extract and search."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(name: str, filename: str):
    path = ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


extract_fa_icons = _load("extract_fa_icons", "extract-fa-icons.py")
search_fa_icons = _load("search_fa_icons", "search-fa-icons.py")


class CatalogTests(unittest.TestCase):
    def test_committed_catalog_is_fa_651(self) -> None:
        catalog = search_fa_icons.load_catalog()
        self.assertEqual(catalog["version"], "6.5.1")
        self.assertEqual(catalog["package"], "@intelstudios/font-awesome")
        by_id = {row["id"]: row for row in catalog["icons"]}
        self.assertIn("building-columns", by_id)
        self.assertIn("university", by_id["building-columns"]["aliases"])
        self.assertNotIn("duotone", by_id["building-columns"]["styles"])
        self.assertIn("github", by_id)
        self.assertEqual(by_id["github"]["styles"], ["brands"])


class SearchTests(unittest.TestCase):
    def test_bank_prefers_building_columns_solid(self) -> None:
        results = search_fa_icons.search_icons("bank")
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["spec"], "fa-building-columns fa-solid fa-fw")
        self.assertEqual(results[0]["variant"], "solid")

    def test_github_uses_brands(self) -> None:
        results = search_fa_icons.search_icons("github")
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["spec"], "fa-github fa-brands fa-fw")
        self.assertEqual(results[0]["variant"], "brands")

    def test_skips_spec_longer_than_50(self) -> None:
        catalog = {
            "icons": [
                {
                    "id": "this-name-is-way-too-long-for-the-column",
                    "styles": ["solid"],
                    "aliases": ["bank"],
                }
            ]
        }
        self.assertEqual(search_fa_icons.search_icons("bank", catalog=catalog), [])

    def test_search_module_has_no_network_client(self) -> None:
        self.assertFalse(hasattr(search_fa_icons, "urllib"))
        self.assertNotIn("urllib", search_fa_icons.__dict__)


class ExtractTests(unittest.TestCase):
    def test_drops_duotone_and_keeps_spec_styles(self) -> None:
        icons = extract_fa_icons.parse_icons_yml(
            {
                "building-columns": {
                    "label": "Building Columns",
                    "styles": ["solid", "regular", "light", "thin", "duotone"],
                    "aliases": {"names": ["bank", "university"]},
                    "search": {"terms": ["bank", "college"]},
                },
                "github": {
                    "label": "GitHub",
                    "styles": ["brands"],
                    "search": {"terms": ["octocat"]},
                },
            }
        )
        by_id = {row["id"]: row for row in icons}
        self.assertEqual(by_id["building-columns"]["styles"], ["solid", "regular", "light", "thin"])
        self.assertEqual(by_id["building-columns"]["aliases"], ["bank", "university"])
        self.assertEqual(by_id["github"]["styles"], ["brands"])


if __name__ == "__main__":
    unittest.main()
