"""Tests for Notification generate/extract."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ot_builder.extract import extract_spec, extract_spec_from_index  # noqa: E402
from ot_builder.hierarchy import build_object_map, dedupe_edges  # noqa: E402
from ot_builder.jsonout import build_object_transfer_json  # noqa: E402
from ot_builder.parse import TransferIndex, find_object_row  # noqa: E402
from ot_builder.rows import build_rows  # noqa: E402
from ot_builder.xml import build_object_transfer_xml  # noqa: E402


FORMAT_HTML = "<p>Request {RequestID}</p><p>{id9999}</p><p>{RequestDetails,100}</p>"


def _base_spec() -> dict:
    return {
        "version": 2,
        "kind": "create_object",
        "object": {"name": "Invoice", "code": "INVOICE", "objectType": "Finance"},
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
                                },
                                {
                                    "name": "Invoice file",
                                    "code": "INVOICE",
                                    "type": "attachment",
                                    "slot": 2,
                                    "width": 50,
                                    "order": 20,
                                    "attachmentStorageId": 0,
                                },
                            ],
                        }
                    ],
                }
            ]
        },
        "roles": {
            "requestor": {"name": "Requestor", "isRequestor": True},
            "owner": {"name": "Owner", "isOwner": True},
        },
        "statuses": {
            "draft": {"name": "Draft", "order": 10},
            "active": {"name": "Active", "order": 20},
        },
        "notifications": [
            {
                "key": "assigned",
                "name": "Assigned to role",
                "type": "single",
                "subject": "{ObjectName} {RequestID}",
                "format": FORMAT_HTML,
                "sendTo": {"requestor": True, "role": True},
                "extra": {"to": "ops@example.com"},
                "conditions": [
                    {"field": "TYPE", "type": "equals_text", "param1": "1"},
                ],
                "attachments": [{"field": "INVOICE"}],
            }
        ],
        "workflow": {
            "mode": "full",
            "name": "Invoice WF",
            "notification": "assigned",
            "steps": [
                {
                    "name": "Draft",
                    "role": "requestor",
                    "status": "draft",
                    "notifications": ["assigned"],
                    "actions": [
                        {
                            "name": "Submit",
                            "role": "owner",
                            "status": "active",
                            "styleId": 1,
                            "order": 10,
                            "notification": "assigned",
                        }
                    ],
                },
                {
                    "name": "Active",
                    "role": "owner",
                    "status": "active",
                },
            ],
        },
        "objectActions": [
            {
                "key": "notify_assigned",
                "name": "Notify assigned",
                "typeCode": "spNotificationDataInsert",
                "order": 10,
                "params": {"NotificationID1": {"notification": "assigned"}},
            }
        ],
        "periodics": [
            {
                "key": "hourly_notify",
                "name": "Hourly notify",
                "requestType": "in_progress",
                "actions": [
                    {
                        "key": "send_mail",
                        "name": "Send mail",
                        "typeCode": "spNotificationDataInsert",
                        "order": 10,
                        "params": {"NotificationID1": {"notification": "assigned"}},
                    }
                ],
            }
        ],
        "ids": {"base": 9500},
    }


class NotificationGenerateTests(unittest.TestCase):
    def test_emits_row_action_fk_condition_attachment_and_param(self) -> None:
        result = build_rows(_base_spec())
        notif = result.rows["Notification"][0]
        self.assertEqual(notif["NotificationName"], "Assigned to role")
        self.assertEqual(notif["NotificationTypeID"], 1)
        self.assertEqual(notif["NotificationSubject"], "{ObjectName} {RequestID}")
        self.assertEqual(notif["NotificationFormat"], FORMAT_HTML)
        self.assertEqual(notif["NotificationEmailRequestor"], 1)
        self.assertEqual(notif["NotificationEmailRole"], 1)
        self.assertEqual(notif["NotificationEmailOwner"], 0)
        self.assertEqual(notif["NotificationToEmailExtra"], "ops@example.com")

        nid = notif["NotificationID"]
        wf = result.rows["Workflow"][0]
        self.assertEqual(wf["NotificationID"], nid)
        submit = next(
            row
            for row in result.rows["WorkflowStepAction"]
            if row["WorkflowStepActionName"] == "Submit"
        )
        self.assertEqual(submit["NotificationID"], nid)

        cond = result.rows["NotificationCondition"][0]
        self.assertEqual(cond["NotificationID"], nid)
        self.assertEqual(cond["NotificationConditionTypeID"], 13)
        type_line = next(
            row for row in result.rows["ObjectLine"] if row["ObjectLineCode"] == "TYPE"
        )
        self.assertEqual(cond["ObjectLineID"], type_line["ObjectLineID"])

        att = result.rows["NotificationAttachment"][0]
        self.assertEqual(att["NotificationID"], nid)
        self.assertEqual(att["NotificationAttachmentIsCompressed"], 1)
        invoice_line = next(
            row for row in result.rows["ObjectLine"] if row["ObjectLineCode"] == "INVOICE"
        )
        self.assertEqual(att["ObjectLineID"], invoice_line["ObjectLineID"])

        param = next(
            row
            for row in result.rows["ObjectActionParam"]
            if row["ObjectActionTypeParamCode"] == "NotificationID1"
        )
        self.assertEqual(str(param["ObjectActionParamValue"]), str(nid))
        periodic_param = next(
            row
            for row in result.rows["PeriodicActionParam"]
            if row["PeriodicActionTypeParamCode"] == "NotificationID1"
        )
        self.assertEqual(str(periodic_param["PeriodicActionParamValue"]), str(nid))

        edges = {
            (e["TableName"], e["ChildTableName"], e["ChildTableRowID"]) for e in result.edges
        }
        self.assertIn(("Workflow", "Notification", nid), edges)
        self.assertIn(("WorkflowStepAction", "Notification", nid), edges)
        self.assertIn(("Notification", "NotificationCondition", cond["NotificationConditionID"]), edges)
        self.assertIn(
            ("Notification", "NotificationAttachment", att["NotificationAttachmentID"]),
            edges,
        )
        oa_id = result.rows["ObjectAction"][0]["ObjectActionID"]
        self.assertIn(("ObjectAction", "Notification", nid), edges)
        pa_id = result.rows["PeriodicAction"][0]["PeriodicActionID"]
        self.assertIn(("PeriodicAction", "Notification", nid), edges)
        self.assertTrue(oa_id)
        self.assertTrue(pa_id)

        step_link = result.rows["WorkflowStepNotification"][0]
        self.assertEqual(step_link["NotificationID"], nid)

    def test_unbound_notification_raises(self) -> None:
        spec = _base_spec()
        spec["workflow"]["notification"] = None
        spec["workflow"]["steps"][0].pop("notifications", None)
        spec["workflow"]["steps"][0]["actions"][0].pop("notification", None)
        spec.pop("objectActions")
        spec.pop("periodics")
        with self.assertRaises(ValueError) as ctx:
            build_rows(spec)
        self.assertIn("not bound", str(ctx.exception))


class NotificationExtractTests(unittest.TestCase):
    def _extract_from_json(self, spec: dict) -> dict:
        result = build_rows(spec)
        text, _omitted = build_object_transfer_json(result.rows)
        payload = json.loads(text)
        parsed = {"rows": payload, "edges": [], "transferInfo": {}}
        index = TransferIndex.from_parsed(parsed)
        return extract_spec_from_index(
            index,
            find_object_row(parsed),
        )

    def test_json_roundtrip_keeps_placeholders_and_bindings(self) -> None:
        extracted = self._extract_from_json(_base_spec())
        notifications = extracted["notifications"]
        self.assertEqual(len(notifications), 1)
        item = notifications[0]
        self.assertEqual(item["key"], "assigned_to_role")
        self.assertEqual(item["type"], "single")
        self.assertEqual(item["subject"], "{ObjectName} {RequestID}")
        self.assertEqual(item["format"], FORMAT_HTML)
        self.assertEqual(item["sendTo"], {"requestor": True, "role": True})
        self.assertEqual(item["extra"], {"to": "ops@example.com"})
        self.assertEqual(item["conditions"][0]["field"], "TYPE")
        self.assertEqual(item["conditions"][0]["type"], "equals_text")
        self.assertEqual(str(item["conditions"][0]["param1"]), "1")
        self.assertEqual(item["attachments"], [{"field": "INVOICE"}])
        self.assertNotIn("compressed", item["attachments"][0])

        workflow = extracted["workflow"]
        self.assertEqual(workflow["notification"], "assigned_to_role")
        draft = next(step for step in workflow["steps"] if step["name"] == "Draft")
        self.assertEqual(draft["notifications"], ["assigned_to_role"])
        self.assertEqual(draft["actions"][0]["notification"], "assigned_to_role")

        self.assertEqual(
            extracted["objectActions"][0]["params"]["NotificationID1"],
            {"notification": "assigned_to_role"},
        )
        self.assertEqual(
            extracted["periodics"][0]["actions"][0]["params"]["NotificationID1"],
            {"notification": "assigned_to_role"},
        )
        explicit = extracted["ids"]["explicit"]
        self.assertIn("assigned_to_role", explicit["notifications"])
        self.assertIn("assigned_to_role/TYPE/equals_text", explicit["notificationConditions"])
        self.assertIn("assigned_to_role/INVOICE", explicit["notificationAttachments"])
        self.assertIn("Draft/assigned_to_role", explicit["workflowStepNotifications"])

    def test_xml_roundtrip_matches_json(self) -> None:
        spec = _base_spec()
        result = build_rows(spec)
        xml_bytes = build_object_transfer_xml(
            result.rows, dedupe_edges(result.edges), build_object_map(dedupe_edges(result.edges))
        )
        with tempfile.TemporaryDirectory() as tmp:
            xml_path = Path(tmp) / "ot.xml"
            xml_path.write_bytes(xml_bytes)
            from_xml = extract_spec(xml_path)
        from_json = self._extract_from_json(spec)
        self.assertEqual(from_xml["notifications"][0]["key"], "assigned_to_role")
        self.assertEqual(from_xml["notifications"][0]["format"], FORMAT_HTML)
        self.assertEqual(from_xml["workflow"]["notification"], from_json["workflow"]["notification"])
        self.assertEqual(
            from_xml["objectActions"][0]["params"]["NotificationID1"],
            {"notification": "assigned_to_role"},
        )


if __name__ == "__main__":
    unittest.main()
