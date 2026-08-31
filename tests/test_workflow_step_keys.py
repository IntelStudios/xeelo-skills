"""Duplicate WorkflowStepName must get distinct Orig. IDs via steps[].key."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ot_builder.extract import extract_spec, extract_spec_from_index  # noqa: E402
from ot_builder.hierarchy import build_object_map, dedupe_edges  # noqa: E402
from ot_builder.parse import TransferIndex, find_object_row, load_transfer  # noqa: E402
from ot_builder.rows import build_rows  # noqa: E402
from ot_builder.xml import build_object_transfer_xml  # noqa: E402


def _dup_step_spec(*, with_explicit_ids: bool = True) -> dict:
    spec: dict = {
        "version": 2,
        "kind": "create_object",
        "object": {"name": "Cars", "code": "CARS", "objectType": "Finance"},
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
                                    "name": "Title",
                                    "code": "TITLE",
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
        "roles": {
            "requestor": {"name": "Requestor", "isRequestor": True},
            "owner": {"name": "Owner", "isOwner": True},
        },
        "statuses": {
            "saved": {"name": "Saved", "order": 10},
            "submitted": {"name": "Submitted", "order": 20},
        },
        "workflow": {
            "mode": "full",
            "name": "Cars WF",
            "steps": [
                {
                    "key": "added_by_system_3698",
                    "name": "Added by system",
                    "role": "requestor",
                    "status": "saved",
                    "actions": [
                        {
                            "key": "submit_4684",
                            "name": "Submit",
                            "role": "owner",
                            "status": "submitted",
                            "styleId": 1,
                            "order": 10,
                        }
                    ],
                    "access": [{"field": "TITLE", "editable": True}],
                },
                {
                    "key": "added_by_system_3700",
                    "name": "Added by system",
                    "role": "owner",
                    "status": "submitted",
                    "actions": [
                        {
                            "key": "submit_4685",
                            "name": "Submit",
                            "role": "requestor",
                            "status": "saved",
                            "styleId": 1,
                            "order": 10,
                        }
                    ],
                },
            ],
        },
        "ids": {"base": 9400},
    }
    if with_explicit_ids:
        spec["ids"]["explicit"] = {
            "workflowSteps": {
                "added_by_system_3698": 3698,
                "added_by_system_3700": 3700,
            },
            "workflowStepActions": {
                "submit_4684": 4684,
                "submit_4685": 4685,
            },
        }
    return spec


class DuplicateWorkflowStepTests(unittest.TestCase):
    def test_generate_emits_distinct_step_ids(self) -> None:
        result = build_rows(_dup_step_spec())
        steps = result.rows["WorkflowStep"]
        self.assertEqual(len(steps), 2)
        ids = [row["WorkflowStepID"] for row in steps]
        self.assertEqual(ids, [3698, 3700])
        self.assertEqual({row["WorkflowStepName"] for row in steps}, {"Added by system"})
        actions = result.rows["WorkflowStepAction"]
        self.assertEqual(sorted(r["WorkflowStepActionID"] for r in actions), [4684, 4685])
        access = result.rows["WorkflowStepAccess"]
        self.assertEqual(access[0]["WorkflowStepID"], 3698)

    def test_extract_roundtrip_keeps_keys_and_orig_ids(self) -> None:
        spec = _dup_step_spec()
        result = build_rows(spec)
        xml_bytes = build_object_transfer_xml(
            result.rows, dedupe_edges(result.edges), build_object_map(dedupe_edges(result.edges))
        )
        with tempfile.TemporaryDirectory() as tmp:
            xml_path = Path(tmp) / "ot.xml"
            xml_path.write_bytes(xml_bytes)
            extracted = extract_spec(xml_path)
            parsed = load_transfer(xml_path)
            from_index = extract_spec_from_index(
                TransferIndex.from_parsed(parsed),
                find_object_row(parsed),
            )
            self.assertEqual(from_index, extracted)

        steps = extracted["workflow"]["steps"]
        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[0]["name"], "Added by system")
        self.assertEqual(steps[1]["name"], "Added by system")
        keys = {s["key"] for s in steps}
        self.assertEqual(keys, {"added_by_system_3698", "added_by_system_3700"})
        explicit = extracted["ids"]["explicit"]["workflowSteps"]
        self.assertEqual(explicit["added_by_system_3698"], 3698)
        self.assertEqual(explicit["added_by_system_3700"], 3700)
        action_keys = {
            a.get("key") or a["name"] for s in steps for a in s.get("actions") or []
        }
        self.assertEqual(action_keys, {"submit_4684", "submit_4685"})

    def test_unique_draft_name_has_no_key(self) -> None:
        spec = _dup_step_spec(with_explicit_ids=False)
        spec["workflow"]["steps"] = [
            {
                "name": "Draft",
                "role": "requestor",
                "status": "saved",
                "actions": [
                    {
                        "name": "Submit",
                        "role": "owner",
                        "status": "submitted",
                        "styleId": 1,
                        "order": 10,
                    }
                ],
            }
        ]
        result = build_rows(spec)
        xml_bytes = build_object_transfer_xml(
            result.rows, dedupe_edges(result.edges), build_object_map(dedupe_edges(result.edges))
        )
        with tempfile.TemporaryDirectory() as tmp:
            xml_path = Path(tmp) / "ot.xml"
            xml_path.write_bytes(xml_bytes)
            extracted = extract_spec(xml_path)

        step = extracted["workflow"]["steps"][0]
        self.assertEqual(step["name"], "Draft")
        self.assertNotIn("key", step)
        self.assertIn("Draft", extracted["ids"]["explicit"]["workflowSteps"])
        action = step["actions"][0]
        self.assertEqual(action["name"], "Submit")
        self.assertNotIn("key", action)


class SuppressSaveTests(unittest.TestCase):
    def test_generate_and_extract_suppress_save(self) -> None:
        spec = _dup_step_spec()
        spec["workflow"]["steps"][0]["suppressSave"] = True
        result = build_rows(spec)
        step = result.rows["WorkflowStep"][0]
        self.assertEqual(step["WorkflowStepIsSuppressSave"], 1)
        xml_bytes = build_object_transfer_xml(
            result.rows, dedupe_edges(result.edges), build_object_map(dedupe_edges(result.edges))
        )
        with tempfile.TemporaryDirectory() as tmp:
            xml_path = Path(tmp) / "ot.xml"
            xml_path.write_bytes(xml_bytes)
            extracted = extract_spec(xml_path)
        self.assertTrue(extracted["workflow"]["steps"][0]["suppressSave"])
        self.assertNotIn("suppressSave", extracted["workflow"]["steps"][1])


class StepActionReopenOnSaveTests(unittest.TestCase):
    def test_generate_and_extract_open_only_assigned(self) -> None:
        spec = _dup_step_spec()
        spec["workflow"]["steps"][0]["actions"][0]["reopenOnSave"] = "open-only-assigned"
        result = build_rows(spec)
        action = result.rows["WorkflowStepAction"][0]
        self.assertEqual(action["WorkflowStepActionReopenTypeID"], 3)
        xml_bytes = build_object_transfer_xml(
            result.rows, dedupe_edges(result.edges), build_object_map(dedupe_edges(result.edges))
        )
        with tempfile.TemporaryDirectory() as tmp:
            xml_path = Path(tmp) / "ot.xml"
            xml_path.write_bytes(xml_bytes)
            extracted = extract_spec(xml_path)
        self.assertEqual(
            extracted["workflow"]["steps"][0]["actions"][0]["reopenOnSave"],
            "open-only-assigned",
        )
        self.assertNotIn("reopenOnSave", extracted["workflow"]["steps"][1]["actions"][0])

    def test_omit_does_not_emit_column(self) -> None:
        result = build_rows(_dup_step_spec())
        for row in result.rows["WorkflowStepAction"]:
            self.assertNotIn("WorkflowStepActionReopenTypeID", row)


class WorkflowIsActiveTests(unittest.TestCase):
    def test_generate_and_extract_inactive_step_and_action(self) -> None:
        spec = _dup_step_spec()
        spec["workflow"]["steps"][1]["isActive"] = False
        spec["workflow"]["steps"][1]["actions"][0]["isActive"] = False
        result = build_rows(spec)
        self.assertEqual(result.rows["WorkflowStep"][0]["IsActive"], 1)
        self.assertEqual(result.rows["WorkflowStep"][1]["IsActive"], 0)
        self.assertEqual(result.rows["WorkflowStepAction"][0]["IsActive"], 1)
        self.assertEqual(result.rows["WorkflowStepAction"][1]["IsActive"], 0)
        xml_bytes = build_object_transfer_xml(
            result.rows, dedupe_edges(result.edges), build_object_map(dedupe_edges(result.edges))
        )
        with tempfile.TemporaryDirectory() as tmp:
            xml_path = Path(tmp) / "ot.xml"
            xml_path.write_bytes(xml_bytes)
            extracted = extract_spec(xml_path)
        self.assertNotIn("isActive", extracted["workflow"]["steps"][0])
        self.assertFalse(extracted["workflow"]["steps"][1]["isActive"])
        self.assertNotIn("isActive", extracted["workflow"]["steps"][0]["actions"][0])
        self.assertFalse(extracted["workflow"]["steps"][1]["actions"][0]["isActive"])


class WorkflowStepAccessExplicitIdsTests(unittest.TestCase):
    def test_extract_records_default_access_orig_ids(self) -> None:
        from ot_builder.extract import _workflow_step_access_specs

        index = TransferIndex.from_parsed(
            {
                "edges": [],
                "rows": {
                    "WorkflowStepAccess": [
                        {
                            "WorkflowStepID": 10,
                            "WorkflowStepAccessID": 1148,
                            "ObjectLineID": 9109,
                            "WorkflowStepAccessIsEditable": False,
                            "WorkflowStepAccessIsVisible": True,
                            "IsActive": True,
                        },
                        {
                            "WorkflowStepID": 10,
                            "WorkflowStepAccessID": 146,
                            "ObjectLineID": 9140,
                            "WorkflowStepAccessIsEditable": True,
                            "WorkflowStepAccessIsVisible": True,
                            "IsActive": True,
                        },
                    ]
                },
                "transferInfo": {},
            }
        )
        explicit: dict[str, int] = {}
        specs = _workflow_step_access_specs(
            index,
            10,
            "Updating",
            {9109: "line_9109_account_number", 9140: "line_9140_name"},
            explicit,
        )
        self.assertEqual(
            specs,
            [{"field": "line_9140_name", "editable": True, "visible": True}],
        )
        self.assertEqual(explicit["Updating/line_9109_account_number"], 1148)
        self.assertEqual(explicit["Updating/line_9140_name"], 146)
