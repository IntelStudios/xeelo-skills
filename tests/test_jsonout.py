"""Tests for Object Transfer JSON emission (download-shaped table→rows)."""

from __future__ import annotations

import json
import sys
import unittest

ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ot_builder.jsonout import (  # noqa: E402
    build_object_transfer_json,
    parse_object_transfer_json_text,
)


class BuildObjectTransferJsonTests(unittest.TestCase):
    def test_omits_empty_tables_and_null_cells(self) -> None:
        text, omitted = build_object_transfer_json(
            {
                "Object": [
                    {
                        "ObjectID": 1,
                        "ObjectName": "Account",
                        "ObjectCode": None,
                        "IsActive": 1,
                    }
                ],
                "ObjectLine": [],
            }
        )
        payload = json.loads(text)
        self.assertEqual(omitted, 0)
        self.assertEqual(list(payload), ["Object"])
        self.assertEqual(payload["Object"][0]["ObjectID"], 1)
        self.assertNotIn("ObjectCode", payload["Object"][0])
        self.assertIs(payload["Object"][0]["IsActive"], True)

    def test_keeps_int_zero_on_non_bit_columns(self) -> None:
        text, _omitted = build_object_transfer_json(
            {
                "Object": [
                    {
                        "ObjectID": 1,
                        "ObjectName": "A",
                        "ObjectCreateCopyType": 0,
                        "IsActive": 0,
                    }
                ]
            }
        )
        row = json.loads(text)["Object"][0]
        self.assertEqual(row["ObjectCreateCopyType"], 0)
        self.assertIs(row["IsActive"], False)

    def test_rejects_all_empty(self) -> None:
        with self.assertRaisesRegex(ValueError, "no table rows"):
            build_object_transfer_json({"Object": [], "ObjectLine": []})

    def test_omits_unchanged_rows_keeps_fk_on_new_rows(self) -> None:
        text, omitted = build_object_transfer_json(
            {
                "Company": [
                    {
                        "CompanyID": 1,
                        "CompanyName": "Company",
                        "CompanyOrder": 0,
                        "IsActive": 1,
                    }
                ],
                "Object": [
                    {
                        "ObjectID": 9003,
                        "ObjectTypeID": 1,
                        "CompanyID": 1,
                        "ObjectName": "TEST_JSON_OT",
                        "IsActive": 1,
                    }
                ],
            },
            baseline={
                "Company": [
                    {
                        "CompanyID": 1,
                        "CompanyName": "Company",
                        "CompanyOrder": 0,
                        "IsActive": True,
                    }
                ],
                "ObjectType": [{"ObjectTypeID": 1, "ObjectTypeName": "Object type"}],
            },
        )
        payload = json.loads(text)
        self.assertEqual(omitted, 1)
        self.assertNotIn("Company", payload)
        self.assertEqual(payload["Object"][0]["CompanyID"], 1)
        self.assertEqual(payload["Object"][0]["ObjectTypeID"], 1)

    def test_keeps_row_when_generated_cells_differ(self) -> None:
        text, omitted = build_object_transfer_json(
            {
                "Company": [
                    {
                        "CompanyID": 1,
                        "CompanyName": "Renamed",
                        "IsActive": 1,
                    }
                ]
            },
            baseline={
                "Company": [
                    {"CompanyID": 1, "CompanyName": "Company", "IsActive": True}
                ]
            },
        )
        payload = json.loads(text)
        self.assertEqual(omitted, 0)
        self.assertEqual(payload["Company"][0]["CompanyName"], "Renamed")


class ParseObjectTransferJsonTests(unittest.TestCase):
    def test_rejects_empty_table_array(self) -> None:
        with self.assertRaisesRegex(ValueError, "empty"):
            parse_object_transfer_json_text('{"Object":[]}')

    def test_accepts_object_rows(self) -> None:
        obj = parse_object_transfer_json_text(
            '{"Object":[{"ObjectID":1,"ObjectName":"A"}]}'
        )
        self.assertEqual(obj["Object"][0]["ObjectID"], 1)


if __name__ == "__main__":
    unittest.main()
