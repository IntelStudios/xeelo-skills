"""Tests for Admin Object Transfer GridModel parsing and process status."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ot_builder.admin_client import (  # noqa: E402
    PROCESS_STATUS_COMPLETED,
    PROCESS_STATUS_FAILED,
    PROCESS_STATUS_PENDING,
    PROCESS_STATUS_PROCESSING,
    _raise_for_info_msg,
    is_terminal_process_status,
    newest_object_transfer_row,
    parse_object_transfer_grid,
)

SAMPLE_GRID = {
    "GridModel": [],
    "DataTable": [
        {
            "ID": 42,
            "COL1_T1_8_File name": "object-transfer.xml",
            "COL1_T9_1_Status": "Real",
            "COL1_T10_2_Status": "Completed",
            "COL1_T12_1_ID": "id42",
            "COL1_B1_12_Message": "Transfer completed successfully",
            "COLOR": "Success",
            "SHORT": "object-transfer.xml",
        },
        {
            "ID": 41,
            "COL1_T1_8_File name": "older.xml",
            "COL1_T9_1_Status": "Test",
            "COL1_T10_2_Status": "Failed",
            "COL1_B1_12_Message": "row error",
            "COLOR": "Danger",
            "SHORT": "older.xml",
        },
        {
            "ID": 40,
            "COL1_T10_2_Status": "Pending",
            "SHORT": "pending.xml",
        },
    ],
}


class ObjectTransferGridTests(unittest.TestCase):
    def test_parses_gridmodel_rows(self) -> None:
        rows = parse_object_transfer_grid(SAMPLE_GRID)
        self.assertEqual([row.xml_id for row in rows], [42, 41, 40])
        self.assertEqual(rows[0].filename, "object-transfer.xml")
        self.assertEqual(rows[0].process_status, PROCESS_STATUS_COMPLETED)
        self.assertEqual(rows[0].test_status, "Real")
        self.assertEqual(rows[0].message, "Transfer completed successfully")
        self.assertEqual(rows[1].process_status, PROCESS_STATUS_FAILED)
        self.assertEqual(rows[2].process_status, PROCESS_STATUS_PENDING)

    def test_parses_nested_datatable(self) -> None:
        payload = {"DataTable": {"Table": [{"ID": 7, "COL1_T10_2_Status": "Processing"}]}}
        rows = parse_object_transfer_grid(payload)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].xml_id, 7)
        self.assertEqual(rows[0].process_status, PROCESS_STATUS_PROCESSING)

    def test_skips_rows_without_id(self) -> None:
        rows = parse_object_transfer_grid({"DataTable": [{"COL1_T10_2_Status": "Completed"}]})
        self.assertEqual(rows, [])

    def test_newest_prefers_unknown_id(self) -> None:
        rows = parse_object_transfer_grid(SAMPLE_GRID)
        picked = newest_object_transfer_row(rows, known_ids={41, 40})
        self.assertIsNotNone(picked)
        assert picked is not None
        self.assertEqual(picked.xml_id, 42)
        fallback = newest_object_transfer_row(rows, known_ids={42, 41, 40})
        self.assertIsNotNone(fallback)
        assert fallback is not None
        self.assertEqual(fallback.xml_id, 42)

    def test_newest_empty(self) -> None:
        self.assertIsNone(newest_object_transfer_row([]))


class ProcessStatusTests(unittest.TestCase):
    def test_terminal_mapping(self) -> None:
        self.assertTrue(is_terminal_process_status(PROCESS_STATUS_COMPLETED))
        self.assertTrue(is_terminal_process_status(PROCESS_STATUS_FAILED))
        self.assertFalse(is_terminal_process_status(PROCESS_STATUS_PENDING))
        self.assertFalse(is_terminal_process_status(PROCESS_STATUS_PROCESSING))
        self.assertFalse(is_terminal_process_status(""))

    def test_raise_for_danger_info_msg(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "no data"):
            _raise_for_info_msg(
                {"MsgType": "danger", "MsgText": "There are no data in selected XML file."},
                "Object Transfer process xmlId=1",
            )

    def test_raise_for_ongoing_warning(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "already ongoing"):
            _raise_for_info_msg(
                {
                    "MsgType": "WARNING",
                    "MsgText": "There is already ongoing object or database setup transfer.",
                },
                "Object Transfer process xmlId=1",
            )

    def test_success_info_msg_ok(self) -> None:
        _raise_for_info_msg(
            {"MsgType": "success", "MsgText": "Data are being processed."},
            "Object Transfer process xmlId=1",
        )


if __name__ == "__main__":
    unittest.main()
