"""Parser for GraphQL DB transfer JSON (table → row arrays)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ot_builder.db_parse import (  # noqa: E402
    TransferIndex,
    load_db_transfer,
    parse_db_transfer_json,
)


def _minimal_db_json(**overrides: object) -> dict:
    payload: dict = {
        "Company": [
            {"CompanyID": 1, "CompanyName": "KB", "IsActive": True},
        ],
        "ObjectType": [
            {"ObjectTypeID": 1, "ObjectTypeName": "General"},
        ],
        "Object": [
            {
                "ObjectID": 10,
                "ObjectName": "Cars",
                "ObjectCode": "CARS",
                "ObjectTypeID": 1,
                "CompanyID": 1,
                "IsActive": True,
            }
        ],
        "ObjectLine": [],
        "AttachmentStorage": [
            {
                "AttachmentStorageID": 1,
                "AttachmentStorageUsername": "-",
                "AttachmentStoragePassword": "-",
                "AttachmentStorageConnectionParams": "-",
            }
        ],
        "GeneralVariable": [
            {"GeneralVariableID": 1, "GeneralVariableCode": "X", "GeneralVariableValue": "-"}
        ],
    }
    payload.update(overrides)
    return payload


class ParseDbTransferJsonTests(unittest.TestCase):
    def test_tables_bits_and_empty_arrays(self) -> None:
        parsed = parse_db_transfer_json(json.dumps(_minimal_db_json()))
        self.assertEqual(parsed["edges"], [])
        self.assertEqual(parsed["objectMap"], [])
        self.assertEqual(parsed["transferInfo"], {})
        company = parsed["rows"]["Company"][0]
        self.assertEqual(company["CompanyID"], 1)
        self.assertIs(company["IsActive"], True)
        self.assertEqual(parsed["rows"]["ObjectLine"], [])
        self.assertEqual(parsed["rows"]["AttachmentStorage"][0]["AttachmentStorageUsername"], "-")

    def test_omitted_null_column(self) -> None:
        payload = _minimal_db_json()
        payload["Object"][0].pop("ObjectCode", None)
        parsed = parse_db_transfer_json(json.dumps(payload))
        self.assertNotIn("ObjectCode", parsed["rows"]["Object"][0])

    def test_inactive_bit_false(self) -> None:
        payload = _minimal_db_json()
        payload["Company"][0]["IsActive"] = False
        parsed = parse_db_transfer_json(json.dumps(payload))
        self.assertIs(parsed["rows"]["Company"][0]["IsActive"], False)

    def test_rejects_non_object_root(self) -> None:
        with self.assertRaisesRegex(ValueError, "object keyed by table"):
            parse_db_transfer_json("[]")

    def test_rejects_non_array_table(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be an array"):
            parse_db_transfer_json('{"Object": {}}')

    def test_rejects_non_object_row(self) -> None:
        with self.assertRaisesRegex(ValueError, r"Object\[0\] must be an object"):
            parse_db_transfer_json('{"Object": [1]}')

    def test_index_pk_and_fk(self) -> None:
        parsed = parse_db_transfer_json(
            json.dumps(
                {
                    "ObjectLine": [
                        {"ObjectLineID": 3, "ObjectID": 9, "ObjectLineCode": "TITLE"},
                        {"ObjectLineID": 4, "ObjectID": 9, "ObjectLineCode": "AMOUNT"},
                    ]
                }
            )
        )
        index = TransferIndex.from_parsed(parsed)
        self.assertEqual(index.row_by_id("ObjectLine", 4)["ObjectLineCode"], "AMOUNT")
        self.assertEqual(len(index.rows_for("ObjectLine", "ObjectID", 9)), 2)
        self.assertEqual(index.rows_for("ObjectLine", "ObjectID", 1), [])

    def test_load_db_transfer_json_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "site.json"
            path.write_text(json.dumps(_minimal_db_json()), encoding="utf-8")
            parsed = load_db_transfer(path)
            self.assertEqual(parsed["rows"]["Object"][0]["ObjectName"], "Cars")

            xml_path = Path(tmp) / "site.xml"
            xml_path.write_text("<XMLData/>", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, r"must be a \.json file"):
                load_db_transfer(xml_path)


if __name__ == "__main__":
    unittest.main()
