"""New workflow: fail role/status default to the header initial pair."""

from __future__ import annotations

import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from ot_builder.extract import _apply_extracted_workflow_fail, extract_spec  # noqa: E402
from ot_builder.hierarchy import build_object_map, dedupe_edges  # noqa: E402
from ot_builder.rows import build_rows  # noqa: E402
from ot_builder.xml import build_object_transfer_xml  # noqa: E402
from test_reopen_on_save import _base_spec  # noqa: E402
from test_workflow_step_keys import _dup_step_spec  # noqa: E402


def _roundtrip(spec: dict) -> dict:
    result = build_rows(spec)
    xml_bytes = build_object_transfer_xml(
        result.rows, dedupe_edges(result.edges), build_object_map(dedupe_edges(result.edges))
    )
    with tempfile.TemporaryDirectory() as tmp:
        xml_path = Path(tmp) / "ot.xml"
        xml_path.write_bytes(xml_bytes)
        return extract_spec(xml_path)


def _named_id(rows: list[dict], id_col: str, name_col: str, name: str) -> int:
    for row in rows:
        if row[name_col] == name:
            return int(row[id_col])
    raise AssertionError(f"missing {name}")


class WorkflowFailDefaultTests(unittest.TestCase):
    def test_minimal_fail_matches_initial(self) -> None:
        result = build_rows(_base_spec())
        wf = result.rows["Workflow"][0]
        self.assertEqual(wf["WorkflowFailRoleID"], wf["RoleID"])
        self.assertEqual(wf["WorkflowFailRequestStatusID"], wf["RequestStatusID"])
        self.assertNotIn("WorkflowFailNotificationID", wf)
        requestor = _named_id(result.rows["Role"], "RoleID", "RoleName", "Requestor")
        draft = _named_id(result.rows["RequestStatus"], "RequestStatusID", "RequestStatusName", "Draft")
        self.assertEqual(wf["WorkflowFailRoleID"], requestor)
        self.assertEqual(wf["WorkflowFailRequestStatusID"], draft)
        extracted = _roundtrip(_base_spec())
        self.assertEqual(extracted["workflow"]["mode"], "minimal")
        self.assertNotIn("failRole", extracted["workflow"])
        self.assertNotIn("failStatus", extracted["workflow"])

    def test_full_fail_matches_first_step(self) -> None:
        result = build_rows(_dup_step_spec())
        wf = result.rows["Workflow"][0]
        first = result.rows["WorkflowStep"][0]
        self.assertEqual(wf["RoleID"], first["RoleID"])
        self.assertEqual(wf["RequestStatusID"], first["RequestStatusID"])
        self.assertEqual(wf["WorkflowFailRoleID"], first["RoleID"])
        self.assertEqual(wf["WorkflowFailRequestStatusID"], first["RequestStatusID"])
        extracted = _roundtrip(_dup_step_spec())
        self.assertNotIn("failRole", extracted["workflow"])
        self.assertNotIn("failStatus", extracted["workflow"])

    def test_override_and_extract(self) -> None:
        spec = _dup_step_spec()
        spec["workflow"]["failRole"] = "owner"
        spec["workflow"]["failStatus"] = "submitted"
        result = build_rows(spec)
        wf = result.rows["Workflow"][0]
        owner = _named_id(result.rows["Role"], "RoleID", "RoleName", "Owner")
        submitted = _named_id(
            result.rows["RequestStatus"], "RequestStatusID", "RequestStatusName", "Submitted"
        )
        self.assertNotEqual(wf["WorkflowFailRoleID"], wf["RoleID"])
        self.assertEqual(wf["WorkflowFailRoleID"], owner)
        self.assertEqual(wf["WorkflowFailRequestStatusID"], submitted)
        fail_edges = [
            edge
            for edge in result.edges
            if edge["TableName"] == "Workflow"
            and edge["TableRowID"] == wf["WorkflowID"]
            and edge["ChildTableRowID"] in (owner, submitted)
        ]
        self.assertTrue(any(edge["ChildTableName"] == "Role" and edge["ChildTableRowID"] == owner for edge in fail_edges))
        self.assertTrue(
            any(
                edge["ChildTableName"] == "RequestStatus" and edge["ChildTableRowID"] == submitted
                for edge in fail_edges
            )
        )
        extracted = _roundtrip(spec)
        self.assertEqual(extracted["workflow"]["failRole"], "owner")
        self.assertEqual(extracted["workflow"]["failStatus"], "submitted")

    def test_reuse_does_not_emit_workflow(self) -> None:
        spec = deepcopy(_dup_step_spec())
        spec["workflow"]["reuse"] = True
        spec["ids"]["explicit"]["workflowId"] = 4
        result = build_rows(spec)
        self.assertNotIn("Workflow", result.rows)

    def test_extract_skips_empty_or_matching_fail(self) -> None:
        workflow: dict = {}
        _apply_extracted_workflow_fail(
            workflow,
            {"RoleID": 1, "RequestStatusID": 2},
            {1: "requestor", 3: "owner"},
            {2: "draft", 4: "active"},
        )
        self.assertEqual(workflow, {})
        _apply_extracted_workflow_fail(
            workflow,
            {
                "RoleID": 1,
                "RequestStatusID": 2,
                "WorkflowFailRoleID": 1,
                "WorkflowFailRequestStatusID": 2,
            },
            {1: "requestor"},
            {2: "draft"},
        )
        self.assertEqual(workflow, {})
        _apply_extracted_workflow_fail(
            workflow,
            {
                "RoleID": 1,
                "RequestStatusID": 2,
                "WorkflowFailRoleID": 3,
                "WorkflowFailRequestStatusID": 2,
            },
            {1: "requestor", 3: "owner"},
            {2: "draft"},
        )
        self.assertEqual(workflow, {"failRole": "owner"})


if __name__ == "__main__":
    unittest.main()
