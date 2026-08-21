"""Tests for full DB transfer env extraction."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ot_builder.db_extract import extract_env  # noqa: E402
from ot_builder.db_parse import load_db_transfer  # noqa: E402


def _latest_lz_json() -> Path | None:
    snaps = ROOT / "projects/lz/snapshots"
    if not snaps.is_dir():
        return None
    files = sorted(snaps.glob("*/*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def _minimal_db_json(*, objects: bool = True) -> dict:
    payload = {
        "Company": [
            {"CompanyID": 1, "CompanyName": "KB", "IsActive": True},
        ],
        "ObjectType": [
            {"ObjectTypeID": 1, "ObjectTypeName": "General"},
        ],
        "Object": [],
        "ObjectLine": [],
    }
    if objects:
        payload["Object"] = [
            {
                "ObjectID": 10,
                "ObjectName": "Cars",
                "ObjectCode": "CARS",
                "ObjectTypeID": 1,
                "CompanyID": 1,
                "IsActive": True,
            }
        ]
    return payload


class ExtractEnvTests(unittest.TestCase):
    def setUp(self) -> None:
        if yaml is None:
            self.skipTest("PyYAML not installed")
        self._tmpdir = tempfile.TemporaryDirectory()
        self.env_dir = Path(self._tmpdir.name) / "env"

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_extracts_all_catalog_objects(self) -> None:
        transfer = _latest_lz_json()
        if transfer is None:
            self.skipTest("lz JSON snapshot not present")

        summary = extract_env(transfer, self.env_dir)

        self.assertGreaterEqual(summary["catalogObjects"], 1)
        self.assertEqual(len(summary["extractedObjects"]), summary["catalogObjects"])
        self.assertEqual(summary["extractMode"], "all")
        self.assertNotIn("companyIdFilter", summary)
        slugs = {item["slug"] for item in summary["extractedObjects"]}
        self.assertIn("transakce", slugs)
        self.assertTrue((self.env_dir / "objects/transakce/xeelo-spec.yaml").is_file())

    def test_empty_site_extracts_zero_objects(self) -> None:
        transfer = Path(self._tmpdir.name) / "empty.json"
        transfer.write_text(json.dumps(_minimal_db_json(objects=False)), encoding="utf-8")

        summary = extract_env(transfer, self.env_dir)

        self.assertEqual(summary["catalogObjects"], 0)
        self.assertEqual(summary["extractedObjects"], [])
        self.assertEqual(summary["extractMode"], "all")
        self.assertFalse(any(self.env_dir.joinpath("objects").iterdir()))

    def test_clears_stale_object_dirs_on_reextract(self) -> None:
        transfer = _latest_lz_json()
        if transfer is None:
            self.skipTest("lz JSON snapshot not present")

        stale = self.env_dir / "objects" / "stale-object"
        stale.mkdir(parents=True)
        (stale / "xeelo-spec.yaml").write_text("stale: true\n", encoding="utf-8")

        summary = extract_env(transfer, self.env_dir)

        self.assertGreaterEqual(len(summary["extractedObjects"]), 1)
        self.assertFalse(stale.exists())
        slugs = {item["slug"] for item in summary["extractedObjects"]}
        self.assertIn("transakce", slugs)

    def test_extract_summary_written(self) -> None:
        transfer = _latest_lz_json()
        if transfer is None:
            self.skipTest("lz JSON snapshot not present")

        extract_env(transfer, self.env_dir)
        summary_path = self.env_dir / "extract-summary.yaml"
        self.assertTrue(summary_path.is_file())
        on_disk = yaml.safe_load(summary_path.read_text(encoding="utf-8"))
        self.assertEqual(on_disk["extractMode"], "all")
        self.assertNotIn("companyIdFilter", on_disk)

    def test_ids_base_is_per_table_map(self) -> None:
        transfer = _latest_lz_json()
        if transfer is None:
            self.skipTest("lz JSON snapshot not present")

        extract_env(transfer, self.env_dir)
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

    def test_catalog_omits_version_without_transfer_info(self) -> None:
        transfer = Path(self._tmpdir.name) / "site.json"
        transfer.write_text(json.dumps(_minimal_db_json()), encoding="utf-8")
        extract_env(transfer, self.env_dir)
        catalog = yaml.safe_load((self.env_dir / "catalog.yaml").read_text(encoding="utf-8"))
        self.assertEqual(catalog["source"]["transferType"], "DB")
        self.assertNotIn("version", catalog["source"])


class ExtractEnvParseOnceTests(unittest.TestCase):
    def test_load_db_transfer_called_once(self) -> None:
        if yaml is None:
            self.skipTest("PyYAML not installed")
        with tempfile.TemporaryDirectory() as tmp:
            transfer = Path(tmp) / "site.json"
            transfer.write_text(json.dumps(_minimal_db_json()), encoding="utf-8")
            env_dir = Path(tmp) / "env"
            with patch("ot_builder.db_extract.load_db_transfer", wraps=load_db_transfer) as mocked:
                summary = extract_env(transfer, env_dir)
            self.assertEqual(mocked.call_count, 1)
            self.assertEqual(summary["catalogObjects"], 1)
            self.assertTrue((env_dir / "objects/cars/xeelo-spec.yaml").is_file())


if __name__ == "__main__":
    unittest.main()
