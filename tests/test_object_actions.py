"""Tests for templates, extended validation, and ObjectAction generate/extract."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ot_builder.extract import extract_spec  # noqa: E402
from ot_builder.ids import IdRegistry  # noqa: E402
from ot_builder.rows import build_rows  # noqa: E402
from ot_builder.templates import (  # noqa: E402
    compile_extended_condition,
    decompile_extended_condition,
    require_template_line_id,
)
from ot_builder.xml import build_object_transfer_xml  # noqa: E402
from ot_builder.hierarchy import build_object_map, dedupe_edges  # noqa: E402


def _account_like_spec() -> dict:
    return {
        "version": 2,
        "kind": "create_object",
        "object": {"name": "Account", "code": "ACCOUNT", "objectType": "Finance"},
        "company": {"name": "KB"},
        "sources": {
            "account_type": {
                "name": "Account Type",
                "typeId": 1,
                "values": [{"value": "FIO", "label": "FIO", "bind": "FIO"}],
            }
        },
        "layout": {
            "tabs": [
                {
                    "name": "General",
                    "placement": 0,
                    "order": 10,
                    "sections": [
                        {
                            "name": "Balance",
                            "order": 10,
                            "width": 100,
                            "fields": [
                                {
                                    "name": "Balance",
                                    "code": "BALANCE",
                                    "type": "number",
                                    "slot": 1,
                                    "width": 50,
                                    "order": 10,
                                    "precision": 2,
                                }
                            ],
                        },
                        {
                            "name": "Bank account",
                            "order": 20,
                            "width": 100,
                            "fields": [
                                {
                                    "name": "Type",
                                    "code": "TYPE",
                                    "type": "combobox",
                                    "slot": 2,
                                    "width": 50,
                                    "order": 20,
                                    "reference": {"source": "account_type"},
                                },
                                {
                                    "name": "Account Number",
                                    "code": "ACCOUNT_NUMBER",
                                    "type": "text",
                                    "slot": 3,
                                    "width": 50,
                                    "order": 30,
                                },
                            ],
                        },
                    ],
                },
                {
                    "name": "FIO",
                    "placement": 1,
                    "order": 20,
                    "sections": [
                        {
                            "name": "Connection",
                            "order": 10,
                            "width": 100,
                            "fields": [
                                {
                                    "name": "FIO API key",
                                    "code": "FIO_API_KEY",
                                    "type": "text",
                                    "slot": 4,
                                    "width": 100,
                                    "order": 10,
                                }
                            ],
                        },
                        {
                            "name": "Transactions",
                            "order": 20,
                            "width": 100,
                            "fields": [
                                {
                                    "name": "Load transactions",
                                    "code": "LOAD_TX",
                                    "type": "button",
                                    "slot": 5,
                                    "width": 50,
                                    "order": 20,
                                },
                                {
                                    "name": "Result",
                                    "code": "RESULT_MEMO",
                                    "type": "memo",
                                    "slot": 6,
                                    "width": 100,
                                    "order": 30,
                                },
                            ],
                        },
                    ],
                },
            ]
        },
        "roles": {"requestor": {"name": "Requestor", "isRequestor": True}},
        "statuses": {"open": {"name": "Open", "order": 10, "isCompleted": False}},
        "workflow": {
            "mode": "full",
            "name": "Account",
            "steps": [
                {
                    "name": "Draft",
                    "role": "requestor",
                    "status": "open",
                    "actions": [],
                    "access": [{"field": "LOAD_TX", "editable": True}],
                }
            ],
        },
        "templates": [
            {
                "key": "cash_register",
                "name": "Cash register",
                "isDefault": True,
                "fields": {
                    "TYPE": {"hidden": True},
                    "ACCOUNT_NUMBER": {"hidden": True},
                    "FIO_API_KEY": {"hidden": True},
                    "LOAD_TX": {"hidden": True},
                    "RESULT_MEMO": {"hidden": True},
                },
            },
            {
                "key": "bank",
                "name": "Bank",
                "fields": {
                    "TYPE": {"mandatory": True},
                    "ACCOUNT_NUMBER": {"mandatory": True},
                    "FIO_API_KEY": {
                        "extended": {"hidden": "id{TYPE} != {account_type.FIO}"}
                    },
                    "LOAD_TX": {"extended": {"hidden": "id{TYPE} != {account_type.FIO}"}},
                },
            },
        ],
        "objectActions": [
            {
                "key": "load-transactions",
                "name": "Load transactions",
                "typeCode": "spEndPointRunNodeJSMainLast",
                "order": 10,
                "workflowSteps": ["Draft"],
                "params": {
                    "CustomJS": "export async function main() { return \"OK\"; }",
                    "EndPointRunWait": "1",
                    "EndPointRunESM": "1",
                    "ApplicableEventType": "Save,SaveNew",
                    "ResponseTextObjectLineID": {"field": "RESULT_MEMO"},
                },
                "conditions": [{"field": "LOAD_TX", "type": "equals_text", "param1": "1"}],
            }
        ],
        "ids": {"base": 9100},
    }


class ExtendedValidationTests(unittest.TestCase):
    def test_compile_uses_field_id_and_source_bind(self) -> None:
        spec = _account_like_spec()
        registry = IdRegistry(spec)
        type_id = registry.require("fields", "TYPE")
        compiled = compile_extended_condition(
            "id{TYPE} != {account_type.FIO}", spec, registry
        )
        self.assertEqual(compiled, f"id{type_id} != 'FIO'")

    def test_compile_numeric_bind_stays_unquoted(self) -> None:
        spec = _account_like_spec()
        spec["sources"]["account_type"]["values"] = [
            {"value": "FIO", "bind": "2"},
        ]
        registry = IdRegistry(spec)
        type_id = registry.require("fields", "TYPE")
        compiled = compile_extended_condition(
            "id{TYPE} != {account_type.FIO}", spec, registry
        )
        self.assertEqual(compiled, f"id{type_id} != 2")

    def test_decompile_roundtrip_placeholders(self) -> None:
        spec = _account_like_spec()
        registry = IdRegistry(spec)
        type_id = registry.require("fields", "TYPE")
        compiled = f"id{type_id} != 'FIO'"
        restored = decompile_extended_condition(
            compiled,
            {type_id: "TYPE"},
            spec["sources"],
        )
        self.assertEqual(restored, "id{TYPE} != {account_type.FIO}")

    def test_decompile_legacy_unquoted_bind(self) -> None:
        spec = _account_like_spec()
        registry = IdRegistry(spec)
        type_id = registry.require("fields", "TYPE")
        restored = decompile_extended_condition(
            f"id{type_id} != FIO",
            {type_id: "TYPE"},
            spec["sources"],
        )
        self.assertEqual(restored, "id{TYPE} != {account_type.FIO}")


class TemplateAndActionGenerateTests(unittest.TestCase):
    def test_two_templates_and_nodejs_action(self) -> None:
        result = build_rows(_account_like_spec())
        sources = result.rows["ObjectLineSource"]
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["ObjectLineSourceStyleID"], 4)
        defaults = result.rows["ObjectDefault"]
        self.assertEqual(len(defaults), 2)
        names = {row["ObjectDefaultName"] for row in defaults}
        self.assertEqual(names, {"Cash register", "Bank"})
        default_flags = {row["ObjectDefaultName"]: row["ObjectDefaultIsDefault"] for row in defaults}
        self.assertEqual(default_flags["Cash register"], 1)
        self.assertEqual(default_flags["Bank"], 0)

        lines = result.rows["ObjectLine"]
        types = {row["ObjectLineCode"]: row["ObjectLineTypeID"] for row in lines}
        self.assertEqual(types["LOAD_TX"], 18)
        self.assertEqual(types["RESULT_MEMO"], 11)

        template_lines = result.rows["ObjectDefaultLine"]
        self.assertEqual(len(template_lines), 12)
        hidden_true = [
            tl
            for tl in template_lines
            if tl.get("ObjectDefaultLineValidationExtHiddenCondition") == "true"
        ]
        self.assertGreaterEqual(len(hidden_true), 5)
        fio_hidden = [
            tl
            for tl in template_lines
            if "'FIO'" in str(tl.get("ObjectDefaultLineValidationExtHiddenCondition") or "")
        ]
        self.assertEqual(len(fio_hidden), 2)
        type_id = next(row["ObjectLineID"] for row in lines if row["ObjectLineCode"] == "TYPE")
        self.assertTrue(
            all(
                tl["ObjectDefaultLineValidationExtHiddenCondition"] == f"id{type_id} != 'FIO'"
                for tl in fio_hidden
            )
        )

        access = result.rows["WorkflowStepAccess"]
        self.assertEqual(len(access), 1)
        load_tx_id = next(row["ObjectLineID"] for row in lines if row["ObjectLineCode"] == "LOAD_TX")
        self.assertEqual(access[0]["ObjectLineID"], load_tx_id)
        self.assertEqual(access[0]["WorkflowStepAccessIsEditable"], 1)
        self.assertEqual(access[0]["WorkflowStepAccessIsVisible"], 1)

        actions = result.rows["ObjectAction"]
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["ObjectActionTypeCode"], "spEndPointRunNodeJSMainLast")
        params = {
            row["ObjectActionTypeParamCode"]: row["ObjectActionParamValue"]
            for row in result.rows["ObjectActionParam"]
        }
        memo_id = next(row["ObjectLineID"] for row in lines if row["ObjectLineCode"] == "RESULT_MEMO")
        self.assertEqual(params["ResponseTextObjectLineID"], str(memo_id))
        self.assertIn("return \"OK\"", params["CustomJS"])
        self.assertEqual(len(result.rows["ObjectActionCondition"]), 1)
        self.assertEqual(len(result.rows["WorkflowStepObjectAction"]), 1)

    def test_roundtrip_extract_keeps_templates_and_action(self) -> None:
        spec = _account_like_spec()
        result = build_rows(spec)
        xml_bytes = build_object_transfer_xml(
            result.rows, dedupe_edges(result.edges), build_object_map(dedupe_edges(result.edges))
        )
        with tempfile.TemporaryDirectory() as tmp:
            xml_path = Path(tmp) / "ot.xml"
            xml_path.write_bytes(xml_bytes)
            extracted = extract_spec(xml_path)

        self.assertEqual(len(extracted["templates"]), 2)
        bank = next(t for t in extracted["templates"] if t["key"] == "bank")
        hidden = bank["fields"]["FIO_API_KEY"]["extended"]["hidden"]
        self.assertEqual(hidden, "id{TYPE} != {account_type.FIO}")
        actions = extracted["objectActions"]
        self.assertEqual(actions[0]["typeCode"], "spEndPointRunNodeJSMainLast")
        self.assertEqual(actions[0]["params"]["ResponseTextObjectLineID"], {"field": "RESULT_MEMO"})
        self.assertEqual(actions[0]["workflowSteps"], ["Draft"])
        draft = next(s for s in extracted["workflow"]["steps"] if s["name"] == "Draft")
        self.assertEqual(
            draft["access"],
            [{"field": "LOAD_TX", "editable": True, "visible": True}],
        )


def _line_types_spec() -> dict:
    return {
        "version": 2,
        "kind": "create_object",
        "object": {"name": "Line types", "code": "LINE_TYPES", "objectType": "General"},
        "company": {"name": "KB"},
        "sources": {
            "account_type": {
                "name": "Account Type",
                "typeId": 1,
                "values": [{"value": "FIO", "label": "FIO", "bind": "FIO"}],
            }
        },
        "layout": {
            "tabs": [
                {
                    "name": "Main",
                    "placement": 0,
                    "order": 10,
                    "sections": [
                        {
                            "name": "Fields",
                            "order": 10,
                            "width": 100,
                            "fields": [
                                {
                                    "name": "Qty",
                                    "code": "QTY",
                                    "type": "number",
                                    "slot": 1,
                                    "precision": 0,
                                    "numberSeparator": ",",
                                    "numberMin": 0,
                                    "numberMax": 99,
                                    "uniqueId": 1,
                                },
                                {
                                    "name": "Price",
                                    "code": "PRICE",
                                    "type": "number",
                                    "slot": 2,
                                    "precision": 2,
                                },
                                {
                                    "name": "Total",
                                    "code": "TOTAL",
                                    "type": "number",
                                    "slot": 3,
                                    "precision": 2,
                                },
                                {
                                    "name": "Name",
                                    "code": "NAME",
                                    "type": "text",
                                    "slot": 4,
                                    "textInputType": 1,
                                },
                                {
                                    "name": "Flag",
                                    "code": "FLAG",
                                    "type": "checkbox",
                                    "slot": 5,
                                },
                                {
                                    "name": "Type",
                                    "code": "TYPE",
                                    "type": "combobox",
                                    "slot": 6,
                                    "isReferenceLink": True,
                                    "reference": {"source": "account_type"},
                                },
                                {
                                    "name": "Kind",
                                    "code": "KIND",
                                    "type": "radio",
                                    "slot": 7,
                                    "columnNumbers": 2,
                                    "reference": {"source": "account_type"},
                                },
                                {
                                    "name": "Tags",
                                    "code": "TAGS",
                                    "type": "checkbox_multiselect",
                                    "slot": 8,
                                    "columnNumbers": 3,
                                    "reference": {"source": "account_type"},
                                },
                                {
                                    "name": "File",
                                    "code": "FILE",
                                    "type": "attachment",
                                    "slot": 9,
                                    "attachmentStorageId": 12,
                                    "ocr": True,
                                    "ocrLang": "en",
                                    "imageResizeMax": 1600,
                                    "mobileScan": True,
                                    "mobileSignature": False,
                                },
                                {
                                    "name": "Preview",
                                    "code": "PREVIEW",
                                    "type": "attachment_preview",
                                    "slot": 10,
                                    "previewField": "FILE",
                                    "previewDownload": False,
                                },
                                {
                                    "name": "Frame",
                                    "code": "FRAME",
                                    "type": "web_frame",
                                    "slot": 11,
                                    "webFrameTypeId": 4,
                                },
                                {
                                    "name": "Notes",
                                    "code": "NOTES",
                                    "type": "memo",
                                    "slot": 12,
                                    "height": 200,
                                },
                                {
                                    "name": "Help",
                                    "code": "HELP",
                                    "type": "description_memo",
                                    "slot": 13,
                                    "descMemoBorder": True,
                                    "descMemoPadding": 8,
                                },
                                {
                                    "name": "Go",
                                    "code": "GO",
                                    "type": "button",
                                    "slot": 14,
                                    "saveAction": 1,
                                    "buttonMessage": "Saved",
                                    "colorFont": "#111111",
                                    "colorBack": "#eeeeee",
                                },
                                {
                                    "name": "Gap",
                                    "code": "GAP",
                                    "type": "empty_space",
                                    "slot": 15,
                                },
                                {
                                    "name": "When",
                                    "code": "WHEN",
                                    "type": "time",
                                    "slot": 16,
                                },
                                {
                                    "name": "Report",
                                    "code": "RPT",
                                    "type": "report",
                                    "slot": 17,
                                    "height": 320,
                                },
                                {
                                    "name": "Server combo",
                                    "code": "SERVER_CB",
                                    "type": "combobox_server",
                                    "slot": 18,
                                    "reference": {"source": "account_type"},
                                },
                                {
                                    "name": "User",
                                    "code": "USER",
                                    "type": "text",
                                    "slot": 19,
                                },
                                {
                                    "name": "Device",
                                    "code": "DEVICE",
                                    "type": "text",
                                    "slot": 20,
                                },
                            ],
                        }
                    ],
                }
            ]
        },
        "templates": [
            {
                "key": "default",
                "name": "Default",
                "isDefault": True,
                "fields": {
                    "TOTAL": {
                        "clientCalculation": {
                            "type": "math",
                            "expr": "id{QTY} * id{PRICE}",
                        },
                        "defaultValue": "0",
                    },
                    "NAME": {
                        "clientCalculation": {
                            "type": "string",
                            "expr": "id{NAME} + ' ' + substring(id{NAME}, 1, 1)",
                        }
                    },
                    "QTY": {
                        "extended": {
                            "hidden": "id{TYPE} != {account_type.FIO}",
                            "disabled": "id{FLAG} ischecked",
                            "mandatory": "id{NAME} isnotempty",
                        }
                    },
                    "HELP": {
                        "defaultValue": "<p>Read this first</p>",
                    },
                    "USER": {
                        "clientCalculation": {
                            "type": "user_info",
                            "expr": "{UserName}",
                        }
                    },
                    "DEVICE": {
                        "clientCalculation": {
                            "type": "device_info",
                            "expr": "{DeviceIP}",
                        }
                    },
                },
            }
        ],
        "ids": {"base": 9200},
    }


class LineTypeExtrasTests(unittest.TestCase):
    def test_generate_extras_client_calc_and_extended(self) -> None:
        result = build_rows(_line_types_spec())
        lines = {row["ObjectLineCode"]: row for row in result.rows["ObjectLine"]}

        self.assertEqual(lines["GAP"]["ObjectLineTypeID"], 6)
        self.assertEqual(lines["FRAME"]["ObjectLineTypeID"], 10)
        self.assertEqual(lines["RPT"]["ObjectLineTypeID"], 13)
        self.assertEqual(lines["SERVER_CB"]["ObjectLineTypeID"], 14)
        self.assertEqual(lines["WHEN"]["ObjectLineTypeID"], 15)
        self.assertEqual(lines["HELP"]["ObjectLineTypeID"], 16)
        self.assertEqual(lines["PREVIEW"]["ObjectLineTypeID"], 17)
        self.assertEqual(lines["TAGS"]["ObjectLineTypeID"], 20)

        self.assertEqual(lines["QTY"]["ObjectLineNumberSeparator"], ",")
        self.assertEqual(lines["QTY"]["ObjectLineNumberMin"], 0)
        self.assertEqual(lines["QTY"]["ObjectLineNumberMax"], 99)
        self.assertEqual(lines["QTY"]["ObjectLineUniqueID"], 1)
        self.assertEqual(lines["NAME"]["ObjectLineTextInputType"], 1)
        self.assertEqual(lines["TYPE"]["ObjectLineIsReferenceLink"], 1)
        self.assertEqual(lines["KIND"]["ObjectLineNumberColumns"], 2)
        self.assertEqual(lines["TAGS"]["ObjectLineNumberColumns"], 3)
        self.assertEqual(lines["FILE"]["AttachmentStorageID"], 12)
        self.assertEqual(lines["FILE"]["ObjectLineAttachmentIsOCR"], 1)
        self.assertEqual(lines["FILE"]["ObjectLineAttachmentOCRLang"], "en")
        self.assertEqual(lines["FILE"]["ObjectLineAttachmentImageResizeMax"], 1600)
        self.assertEqual(lines["FILE"]["ObjectLineAttachmentMobileIsScan"], 1)
        self.assertEqual(lines["FILE"]["ObjectLineAttachmentMobileIsSignature"], 0)
        self.assertEqual(
            lines["PREVIEW"]["ObjectLineAttPreviewObjectLineID"], lines["FILE"]["ObjectLineID"]
        )
        self.assertEqual(lines["PREVIEW"]["ObjectLineAttPreviewIsDownload"], 0)
        self.assertEqual(lines["FRAME"]["WebFrameTypeID"], 4)
        self.assertEqual(lines["NOTES"]["ObjectLineHeight"], 200)
        self.assertEqual(lines["HELP"]["ObjectLineDescMemoIsBorder"], 1)
        self.assertEqual(lines["HELP"]["ObjectLineDescMemoPadding"], 8)
        self.assertEqual(lines["GO"]["ObjectLineButtonSaveAction"], 1)
        self.assertEqual(lines["GO"]["ObjectLineButtonMessage"], "Saved")
        self.assertEqual(lines["GO"]["ObjectLineColorFont"], "#111111")
        self.assertEqual(lines["GO"]["ObjectLineColorBack"], "#eeeeee")
        self.assertEqual(lines["RPT"]["ObjectLineHeight"], 320)

        qty_id = lines["QTY"]["ObjectLineID"]
        price_id = lines["PRICE"]["ObjectLineID"]
        type_id = lines["TYPE"]["ObjectLineID"]
        flag_id = lines["FLAG"]["ObjectLineID"]
        name_id = lines["NAME"]["ObjectLineID"]

        template_lines = {row["ObjectLineID"]: row for row in result.rows["ObjectDefaultLine"]}
        total = template_lines[lines["TOTAL"]["ObjectLineID"]]
        self.assertEqual(total["ObjectDefaultLineClientCalculationTypeID"], 1)
        self.assertEqual(total["ObjectDefaultLineClientCalculation"], f"id{qty_id} * id{price_id}")
        self.assertEqual(total["ObjectDefaultLineValue"], "0")
        self.assertNotIn("1#", total["ObjectDefaultLineClientCalculation"])

        name = template_lines[name_id]
        self.assertEqual(name["ObjectDefaultLineClientCalculationTypeID"], 2)
        self.assertEqual(
            name["ObjectDefaultLineClientCalculation"],
            f"id{name_id} + ' ' + substring(id{name_id}, 1, 1)",
        )

        qty = template_lines[qty_id]
        self.assertEqual(qty["ObjectDefaultLineValidationID"], 9)
        self.assertEqual(
            qty["ObjectDefaultLineValidationExtHiddenCondition"], f"id{type_id} != 'FIO'"
        )
        self.assertEqual(
            qty["ObjectDefaultLineValidationExtDisabledCondition"], f"id{flag_id} ischecked"
        )
        self.assertEqual(
            qty["ObjectDefaultLineValidationExtMandatoryCondition"], f"id{name_id} isnotempty"
        )

        frame = template_lines[lines["FRAME"]["ObjectLineID"]]
        self.assertEqual(frame["ObjectDefaultLineValidationID"], 2)
        go = template_lines[lines["GO"]["ObjectLineID"]]
        self.assertEqual(go["ObjectDefaultLineValidationID"], 2)

        help_line = template_lines[lines["HELP"]["ObjectLineID"]]
        self.assertEqual(help_line["ObjectDefaultLineDescMemo"], "<p>Read this first</p>")
        self.assertNotIn("ObjectDefaultLineValue", help_line)

        user = template_lines[lines["USER"]["ObjectLineID"]]
        self.assertEqual(user["ObjectDefaultLineClientCalculationTypeID"], 7)
        self.assertEqual(user["ObjectDefaultLineClientCalculation"], "{UserName}")
        self.assertNotIn("7#", user["ObjectDefaultLineClientCalculation"])

        device = template_lines[lines["DEVICE"]["ObjectLineID"]]
        self.assertEqual(device["ObjectDefaultLineClientCalculationTypeID"], 8)
        self.assertEqual(device["ObjectDefaultLineClientCalculation"], "{DeviceIP}")
        self.assertNotIn("8#", device["ObjectDefaultLineClientCalculation"])

    def test_roundtrip_extract_extras_and_client_calc(self) -> None:
        spec = _line_types_spec()
        result = build_rows(spec)
        xml_bytes = build_object_transfer_xml(
            result.rows, dedupe_edges(result.edges), build_object_map(dedupe_edges(result.edges))
        )
        with tempfile.TemporaryDirectory() as tmp:
            xml_path = Path(tmp) / "ot.xml"
            xml_path.write_bytes(xml_bytes)
            extracted = extract_spec(xml_path)

        fields = {
            field["code"]: field
            for tab in extracted["layout"]["tabs"]
            for section in tab["sections"]
            for field in section["fields"]
        }
        self.assertEqual(fields["QTY"]["numberSeparator"], ",")
        self.assertEqual(fields["QTY"]["numberMin"], 0)
        self.assertEqual(fields["QTY"]["numberMax"], 99)
        self.assertEqual(fields["QTY"]["uniqueId"], 1)
        self.assertEqual(fields["NAME"]["textInputType"], 1)
        self.assertTrue(fields["TYPE"]["isReferenceLink"])
        self.assertEqual(fields["KIND"]["columnNumbers"], 2)
        self.assertEqual(fields["TAGS"]["columnNumbers"], 3)
        self.assertEqual(fields["FILE"]["attachmentStorageId"], 12)
        self.assertTrue(fields["FILE"]["ocr"])
        self.assertEqual(fields["FILE"]["ocrLang"], "en")
        self.assertEqual(fields["PREVIEW"]["previewField"], "FILE")
        self.assertIs(fields["PREVIEW"]["previewDownload"], False)
        self.assertEqual(fields["FRAME"]["webFrameTypeId"], 4)
        self.assertEqual(fields["NOTES"]["height"], 200)
        self.assertTrue(fields["HELP"]["descMemoBorder"])
        self.assertEqual(fields["HELP"]["descMemoPadding"], 8)
        self.assertEqual(fields["GO"]["buttonMessage"], "Saved")
        self.assertEqual(fields["TAGS"]["type"], "checkbox_multiselect")
        self.assertEqual(fields["SERVER_CB"]["type"], "combobox_server")
        self.assertEqual(fields["GAP"]["type"], "empty_space")

        tmpl = extracted["templates"][0]["fields"]
        self.assertEqual(tmpl["TOTAL"]["clientCalculation"]["type"], "math")
        self.assertEqual(tmpl["TOTAL"]["clientCalculation"]["expr"], "id{QTY} * id{PRICE}")
        self.assertEqual(tmpl["TOTAL"]["defaultValue"], "0")
        self.assertEqual(tmpl["NAME"]["clientCalculation"]["type"], "string")
        self.assertEqual(
            tmpl["NAME"]["clientCalculation"]["expr"],
            "id{NAME} + ' ' + substring(id{NAME}, 1, 1)",
        )
        self.assertEqual(tmpl["QTY"]["extended"]["hidden"], "id{TYPE} != {account_type.FIO}")
        self.assertEqual(tmpl["QTY"]["extended"]["disabled"], "id{FLAG} ischecked")
        self.assertEqual(tmpl["QTY"]["extended"]["mandatory"], "id{NAME} isnotempty")
        self.assertNotIn("FRAME", tmpl)
        self.assertEqual(tmpl["HELP"]["defaultValue"], "<p>Read this first</p>")
        self.assertEqual(tmpl["USER"]["clientCalculation"]["type"], "user_info")
        self.assertEqual(tmpl["USER"]["clientCalculation"]["expr"], "{UserName}")
        self.assertEqual(tmpl["DEVICE"]["clientCalculation"]["type"], "device_info")
        self.assertEqual(tmpl["DEVICE"]["clientCalculation"]["expr"], "{DeviceIP}")

    def test_user_info_requires_placeholder_expr(self) -> None:
        spec = _line_types_spec()
        spec["templates"][0]["fields"]["USER"]["clientCalculation"] = {"type": "user_info"}
        with self.assertRaisesRegex(ValueError, "user_info"):
            build_rows(spec)


class ExtendedConditionCompileTests(unittest.TestCase):
    def test_compile_unary_and_substring_conditions(self) -> None:
        spec = _line_types_spec()
        registry = IdRegistry(spec)
        name_id = registry.require("fields", "NAME")
        flag_id = registry.require("fields", "FLAG")
        self.assertEqual(
            compile_extended_condition("id{NAME} isempty", spec, registry),
            f"id{name_id} isempty",
        )
        self.assertEqual(
            compile_extended_condition("id{FLAG} ischecked", spec, registry),
            f"id{flag_id} ischecked",
        )
        self.assertEqual(
            compile_extended_condition("substring(id{NAME}, 1, 1) = 'I'", spec, registry),
            f"substring(id{name_id}, 1, 1) = 'I'",
        )


class RequestTitleAndHiddenFlagsTests(unittest.TestCase):
    def test_generate_and_extract_title_disabled_hidden(self) -> None:
        spec = {
            "version": 2,
            "kind": "create_object",
            "object": {
                "name": "Account",
                "code": "ACCOUNT",
                "objectType": "Finance",
                "requestTitleField": "TITLE",
            },
            "company": {"name": "KB"},
            "layout": {
                "tabs": [
                    {
                        "name": "General",
                        "placement": 0,
                        "order": 10,
                        "sections": [
                            {
                                "name": "Identity",
                                "order": 10,
                                "width": 100,
                                "fields": [
                                    {
                                        "name": "Name",
                                        "code": "NAME",
                                        "type": "text",
                                        "slot": 1,
                                        "width": 50,
                                        "order": 10,
                                    },
                                    {
                                        "name": "Title",
                                        "code": "TITLE",
                                        "type": "text",
                                        "slot": 2,
                                        "width": 50,
                                        "order": 20,
                                    },
                                ],
                            }
                        ],
                    },
                    {
                        "name": "Helpers",
                        "placement": 1,
                        "order": 20,
                        "alwaysHidden": True,
                        "sections": [
                            {
                                "name": "Hidden",
                                "order": 10,
                                "width": 100,
                                "fields": [
                                    {
                                        "name": "Scratch",
                                        "code": "SCRATCH",
                                        "type": "text",
                                        "slot": 3,
                                        "width": 50,
                                        "order": 10,
                                        "alwaysHidden": True,
                                    }
                                ],
                            }
                        ],
                    },
                ]
            },
            "templates": [
                {
                    "key": "bank",
                    "name": "Bank",
                    "isDefault": True,
                    "fields": {"TITLE": {"alwaysDisabled": True}},
                }
            ],
        }
        result = build_rows(spec)
        obj = result.rows["Object"][0]
        title_id = next(r["ObjectLineID"] for r in result.rows["ObjectLine"] if r["ObjectLineCode"] == "TITLE")
        self.assertEqual(obj["RequestTitleObjectLineID"], title_id)
        scratch = next(r for r in result.rows["ObjectLine"] if r["ObjectLineCode"] == "SCRATCH")
        self.assertEqual(scratch["ObjectLineIsHidden"], 1)
        helpers = next(r for r in result.rows["ObjectLineTab"] if r["ObjectLineTabName"] == "Helpers")
        self.assertEqual(helpers["ObjectLineTabAlwaysHidden"], 1)
        title_tl = next(
            tl
            for tl in result.rows["ObjectDefaultLine"]
            if tl["ObjectLineID"] == title_id
        )
        self.assertEqual(title_tl["ObjectDefaultLineIsDisabled"], 1)

        xml_bytes = build_object_transfer_xml(
            result.rows, dedupe_edges(result.edges), build_object_map(dedupe_edges(result.edges))
        )
        with tempfile.TemporaryDirectory() as tmp:
            xml_path = Path(tmp) / "ot.xml"
            xml_path.write_bytes(xml_bytes)
            extracted = extract_spec(xml_path)

        self.assertEqual(extracted["object"]["requestTitleField"], "TITLE")
        helpers_tab = next(t for t in extracted["layout"]["tabs"] if t["name"] == "Helpers")
        self.assertTrue(helpers_tab["alwaysHidden"])
        scratch_field = helpers_tab["sections"][0]["fields"][0]
        self.assertTrue(scratch_field["alwaysHidden"])
        bank = extracted["templates"][0]
        self.assertTrue(bank["fields"]["TITLE"]["alwaysDisabled"])


class TemplateLineIdTests(unittest.TestCase):
    def test_legacy_accepts_composite_extract_key(self) -> None:
        registry = IdRegistry(
            {"ids": {"explicit": {"objectDefaultLines": {"default/amount": 145}}}}
        )
        self.assertEqual(
            require_template_line_id(registry, "default", "amount", legacy=True),
            145,
        )


if __name__ == "__main__":
    unittest.main()
