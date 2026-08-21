"""Recycled workflow: OT JSON omits WF definition; still binds template and step access."""

from __future__ import annotations

import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from ot_builder.jsonout import build_object_transfer_json  # noqa: E402
from ot_builder.rows import build_rows  # noqa: E402
from test_workflow_step_keys import _dup_step_spec  # noqa: E402


class ReusedWorkflowTests(unittest.TestCase):
    def test_reuse_omits_definition_keeps_access_and_template_bind(self) -> None:
        spec = deepcopy(_dup_step_spec())
        spec["workflow"]["reuse"] = True
        spec["ids"]["explicit"]["workflowId"] = 4
        spec["languageTable"] = {
            "object": {"sk": "Autá"},
            "workflow": {"sk": "shared"},
            "roles": {"requestor": {"sk": "Žiadateľ"}},
            "statuses": {"saved": {"sk": "Uložené"}},
            "stepActions": {"added_by_system_3698/submit_4684": {"sk": "Odoslať"}},
            "lines": {"TITLE": {"sk": "Názov"}},
        }
        result = build_rows(spec)
        for table in (
            "Workflow",
            "WorkflowStep",
            "WorkflowStepAction",
            "Role",
            "RequestStatus",
        ):
            self.assertNotIn(table, result.rows, table)

        access = result.rows["WorkflowStepAccess"]
        self.assertEqual(len(access), 1)
        self.assertEqual(access[0]["WorkflowStepID"], 3698)
        self.assertEqual(access[0]["ObjectLineID"], result.field_meta["TITLE"]["lineId"])

        self.assertEqual(result.rows["ObjectDefault"][0]["WorkflowID"], 4)

        lang_parents = {row["TableName"] for row in result.rows.get("LanguageTable", [])}
        self.assertIn("Object", lang_parents)
        self.assertIn("ObjectLine", lang_parents)
        self.assertNotIn("Workflow", lang_parents)
        self.assertNotIn("Role", lang_parents)
        self.assertNotIn("RequestStatus", lang_parents)
        self.assertNotIn("WorkflowStepAction", lang_parents)

        payload = json.loads(build_object_transfer_json(result.rows)[0])
        self.assertNotIn("Workflow", payload)
        self.assertNotIn("Role", payload)
        self.assertIn("WorkflowStepAccess", payload)
        self.assertIn("ObjectDefault", payload)
        self.assertEqual(payload["ObjectDefault"][0]["WorkflowID"], 4)


if __name__ == "__main__":
    unittest.main()
