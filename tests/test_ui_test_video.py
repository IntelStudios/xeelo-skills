"""Tests for /ui-test result video renderer."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ui_testing" / "scripts"))

from make_ui_test_video import load_manifest, main  # noqa: E402


class ManifestTests(unittest.TestCase):
    def test_rejects_secret_keys(self) -> None:
        tmp = Path(tempfile.mkdtemp()) / "manifest.json"
        tmp.write_text(json.dumps({"title": "x", "userPwd": "nope"}), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "userPwd"):
            load_manifest(tmp)

    def test_allows_password_in_detail_text(self) -> None:
        tmp = Path(tempfile.mkdtemp()) / "manifest.json"
        tmp.write_text(
            json.dumps(
                {
                    "title": "UI test",
                    "overall": "PASS",
                    "steps": [
                        {
                            "label": "Login",
                            "status": "PASS",
                            "detail": "Local password form was visible",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        data = load_manifest(tmp)
        self.assertEqual(data["overall"], "PASS")


class RenderTests(unittest.TestCase):
    def test_writes_mp4(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        manifest = tmp / "manifest.json"
        out = tmp / "result.mp4"
        manifest.write_text(
            json.dumps(
                {
                    "title": "UI test",
                    "subtitle": "fixture",
                    "overall": "FAIL",
                    "note": "Deadline invalid",
                    "steps": [
                        {"label": "Login", "status": "PASS", "detail": "Inbox"},
                        {"label": "Save", "status": "FAIL"},
                    ],
                }
            ),
            encoding="utf-8",
        )
        rc = main(["--manifest", str(manifest), "--out", str(out)])
        self.assertEqual(rc, 0)
        self.assertTrue(out.is_file())
        self.assertGreater(out.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
