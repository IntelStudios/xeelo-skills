"""Tests for Periodic + Scheduler generate/extract."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ot_builder.extract import extract_spec  # noqa: E402
from ot_builder.hierarchy import build_object_map, dedupe_edges  # noqa: E402
from ot_builder.jsonout import build_object_transfer_json  # noqa: E402
from ot_builder.periodics import request_type_id, request_type_slug  # noqa: E402
from ot_builder.rows import build_rows  # noqa: E402
from ot_builder.xml import build_object_transfer_xml  # noqa: E402


def _spec() -> dict:
    return {
        "version": 2,
        "kind": "create_object",
        "object": {"name": "Account", "code": "ACCOUNT", "objectType": "Finance"},
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
                                    "name": "Type",
                                    "code": "TYPE",
                                    "type": "text",
                                    "slot": 1,
                                    "width": 50,
                                    "order": 10,
                                }
                            ],
                        }
                    ],
                }
            ]
        },
        "periodics": [
            {
                "key": "load_fio_hourly",
                "name": "Load FIO transactions",
                "requestType": "completed",
                "cron": "0 0 * ? * * *",
                "conditions": [
                    {"field": "TYPE", "type": "equals_text", "param1": "FIO"}
                ],
                "actions": [
                    {
                        "key": "start_load",
                        "name": "Start load",
                        "typeCode": "spEndPointRunNodeJSMain",
                        "order": 10,
                        "params": {
                            "CustomJS": 'export async function main() { return "OK"; }',
                            "EndPointRunTimeout": "300000",
                        },
                    }
                ],
            }
        ],
        "languageTable": {
            "periodics": {"load_fio_hourly": {"cs": "Načíst FIO transakce"}},
            "periodicActions": {"load_fio_hourly/start_load": {"cs": "Spustit načtení"}},
            "schedulers": {"load_fio_hourly": {"cs": "Hodinový import FIO"}},
        },
        "ids": {"base": 9100},
    }


class PeriodicHelperTests(unittest.TestCase):
    def test_request_type_roundtrip(self) -> None:
        self.assertEqual(request_type_id("completed"), 20)
        self.assertEqual(request_type_id(10), 10)
        self.assertEqual(request_type_slug(0), "all")
        with self.assertRaises(ValueError):
            request_type_id("weekly")


class PeriodicGenerateTests(unittest.TestCase):
    def test_emits_periodic_nodejs_scheduler_and_language(self) -> None:
        result = build_rows(_spec())
        periodic = result.rows["Periodic"][0]
        self.assertEqual(periodic["PeriodicName"], "Load FIO transactions")
        self.assertEqual(periodic["PeriodicRequestTypeID"], 20)
        self.assertEqual(periodic["ObjectID"], result.rows["Object"][0]["ObjectID"])

        cond = result.rows["PeriodicCondition"][0]
        type_id = next(
            row["ObjectLineID"] for row in result.rows["ObjectLine"] if row["ObjectLineCode"] == "TYPE"
        )
        self.assertEqual(cond["ObjectLineID"], type_id)
        self.assertEqual(cond["PeriodicConditionTypeID"], 13)
        self.assertEqual(cond["PeriodicConditionParam1"], "FIO")

        action = result.rows["PeriodicAction"][0]
        self.assertEqual(action["PeriodicActionTypeCode"], "spEndPointRunNodeJSMain")
        params = {
            row["PeriodicActionTypeParamCode"]: row["PeriodicActionParamValue"]
            for row in result.rows["PeriodicActionParam"]
        }
        self.assertEqual(params["EndPointRunWait"], "1")
        self.assertEqual(params["EndPointRunTimeout"], "300000")
        self.assertIn("return \"OK\"", params["CustomJS"])

        scheduler = result.rows["Scheduler"][0]
        self.assertEqual(scheduler["SchedulerCRON"], "0 0 * ? * * *")
        line = result.rows["SchedulerLine"][0]
        self.assertEqual(line["SchedulerLineTypeCode"], "spPeriodicExecute")
        param = result.rows["SchedulerLineParam"][0]
        self.assertEqual(param["SchedulerLineTypeParamCode"], "PeriodicID")
        self.assertEqual(param["SchedulerLineParamValue"], str(periodic["PeriodicID"]))

        lt = result.rows["LanguageTable"]
        tables = {(row["TableName"], row["ColumnName"], row["UserLanguageCode"]) for row in lt}
        self.assertIn(("Periodic", "PeriodicName", "cs"), tables)
        self.assertIn(("PeriodicAction", "PeriodicActionName", "cs"), tables)
        self.assertIn(("Scheduler", "SchedulerName", "cs"), tables)

        text, _omitted = build_object_transfer_json(result.rows)
        payload = json.loads(text)
        self.assertIn("Periodic", payload)
        self.assertIn("Scheduler", payload)
        self.assertTrue(payload["Periodic"][0]["IsActive"] is True)

    def test_xml_roundtrip_extract(self) -> None:
        spec = _spec()
        result = build_rows(spec)
        xml_bytes = build_object_transfer_xml(
            result.rows, dedupe_edges(result.edges), build_object_map(dedupe_edges(result.edges))
        )
        with tempfile.TemporaryDirectory() as tmp:
            xml_path = Path(tmp) / "ot.xml"
            xml_path.write_bytes(xml_bytes)
            extracted = extract_spec(xml_path)

        periodics = extracted["periodics"]
        self.assertEqual(len(periodics), 1)
        periodic = periodics[0]
        self.assertEqual(periodic["key"], "load_fio_transactions")
        self.assertEqual(periodic["requestType"], "completed")
        self.assertEqual(periodic["cron"], "0 0 * ? * * *")
        self.assertEqual(periodic["conditions"][0]["field"], "TYPE")
        self.assertEqual(periodic["conditions"][0]["param1"], "FIO")
        action = periodic["actions"][0]
        self.assertEqual(action["typeCode"], "spEndPointRunNodeJSMain")
        self.assertEqual(str(action["params"]["EndPointRunTimeout"]), "300000")
        self.assertEqual(
            extracted["languageTable"]["periodics"]["load_fio_transactions"]["cs"],
            "Načíst FIO transakce",
        )
        explicit = extracted["ids"]["explicit"]
        self.assertIn("periodics", explicit)
        self.assertIn("schedulers", explicit)
        self.assertIn("load_fio_transactions/start_load", explicit["periodicActions"])


if __name__ == "__main__":
    unittest.main()
