"""Tests for full DB transfer env extraction."""

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

from ot_builder.db_extract import extract_env  # noqa: E402

LZ_TRANSFER = ROOT / "projects/lz/snapshots/20260813_132321/lz_20260813_132321.xml"
LZ_EMPTY_TRANSFER = ROOT / "projects/lz/snapshots/20260813_111646/lz_20260813_111646.xml"


class ExtractEnvTests(unittest.TestCase):
    def setUp(self) -> None:
        if yaml is None:
            self.skipTest("PyYAML not installed")
        self._tmpdir = tempfile.TemporaryDirectory()
        self.env_dir = Path(self._tmpdir.name) / "env"

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_extracts_all_catalog_objects(self) -> None:
        if not LZ_TRANSFER.is_file():
            self.skipTest("lz snapshot not present")

        summary = extract_env(LZ_TRANSFER, self.env_dir)

        self.assertEqual(summary["catalogObjects"], 1)
        self.assertEqual(len(summary["extractedObjects"]), 1)
        self.assertEqual(summary["extractMode"], "all")
        self.assertNotIn("companyIdFilter", summary)
        self.assertTrue((self.env_dir / "objects/transakce/xeelo-spec.yaml").is_file())

    def test_empty_site_extracts_zero_objects(self) -> None:
        if not LZ_EMPTY_TRANSFER.is_file():
            self.skipTest("lz empty snapshot not present")

        summary = extract_env(LZ_EMPTY_TRANSFER, self.env_dir)

        self.assertEqual(summary["catalogObjects"], 0)
        self.assertEqual(summary["extractedObjects"], [])
        self.assertEqual(summary["extractMode"], "all")
        self.assertFalse(any(self.env_dir.joinpath("objects").iterdir()))

    def test_clears_stale_object_dirs_on_reextract(self) -> None:
        if not LZ_TRANSFER.is_file():
            self.skipTest("lz snapshot not present")

        stale = self.env_dir / "objects" / "stale-object"
        stale.mkdir(parents=True)
        (stale / "xeelo-spec.yaml").write_text("stale: true\n", encoding="utf-8")

        summary = extract_env(LZ_TRANSFER, self.env_dir)

        self.assertEqual(len(summary["extractedObjects"]), 1)
        self.assertFalse(stale.exists())
        slugs = {item["slug"] for item in summary["extractedObjects"]}
        self.assertEqual(slugs, {"transakce"})

    def test_extract_summary_written(self) -> None:
        if not LZ_TRANSFER.is_file():
            self.skipTest("lz snapshot not present")

        extract_env(LZ_TRANSFER, self.env_dir)
        summary_path = self.env_dir / "extract-summary.yaml"
        self.assertTrue(summary_path.is_file())
        on_disk = yaml.safe_load(summary_path.read_text(encoding="utf-8"))
        self.assertEqual(on_disk["extractMode"], "all")
        self.assertNotIn("companyIdFilter", on_disk)

    def test_ids_base_is_per_table_map(self) -> None:
        if not LZ_TRANSFER.is_file():
            self.skipTest("lz snapshot not present")

        extract_env(LZ_TRANSFER, self.env_dir)
        ids_path = self.env_dir / "objects/transakce/spec/ids.yaml"
        self.assertTrue(ids_path.is_file())
        data = yaml.safe_load(ids_path.read_text(encoding="utf-8"))
        base = (data.get("ids") or {}).get("base")
        by_table = (data.get("ids") or {}).get("byTable") or {}
        self.assertIsInstance(base, dict)
        self.assertIn("ObjectLine", base)
        line_ids = [int(v) for v in (by_table.get("ObjectLine") or {}).values()]
        if line_ids:
            self.assertGreaterEqual(base["ObjectLine"], max(line_ids))


if __name__ == "__main__":
    unittest.main()
