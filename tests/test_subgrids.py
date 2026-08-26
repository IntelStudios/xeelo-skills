"""Generate/extract roundtrip for spec/subgrids.yaml and parent objectSub bind."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ot_builder.extract import extract_spec  # noqa: E402
from ot_builder.hierarchy import build_object_map, dedupe_edges  # noqa: E402
from ot_builder.rows import build_rows  # noqa: E402
from ot_builder.spec_loader import load_spec, write_spec  # noqa: E402
from ot_builder.xml import build_object_transfer_xml  # noqa: E402


def _base_spec() -> dict:
    return {
        "version": 2,
        "kind": "create_object",
        "object": {"name": "Invoice", "code": "INVOICE", "objectType": "Finance"},
        "company": {"name": "KB"},
        "subgrids": {
            "invoice_lines": {
                "name": "Invoice lines",
                "code": "invoice_lines",
                "layout": {
                    "tabs": [
                        {
                            "name": "General",
                            "placement": 0,
                            "order": 1,
                            "sections": [
                                {
                                    "name": "Details",
                                    "order": 1,
                                    "width": 100,
                                    "fields": [
                                        {
                                            "name": "Description",
                                            "code": "DESC",
                                            "type": "text",
                                            "slot": 1,
                                            "width": 100,
                                            "order": 10,
                                        }
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
                        "fields": {"DESC": {"mandatory": True}},
                    }
                ],
                "onGrid": {
                    "fields": {
                        "DESC": {"allowed": True, "isSearch": True},
                    },
                    "layouts": [
                        {
                            "size": "Large",
                            "type": "Grid",
                            "module": "Items",
                            "placements": [
                                {
                                    "row": "T",
                                    "columns": [
                                        {
                                            "field": "DESC",
                                            "position": 0,
                                            "length": 100,
                                            "valueWidth": 0,
                                            "labelType": 1,
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                },
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
                                },
                                {
                                    "name": "Lines",
                                    "code": "LINES",
                                    "type": "subgrid",
                                    "objectSub": "invoice_lines",
                                    "width": 100,
                                    "order": 20,
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
                "fields": {"LINES": {"subgridTemplate": "default"}},
            }
        ],
        "ids": {"base": 9100},
    }


class SubgridGenerateTests(unittest.TestCase):
    def test_emits_object_sub_tree_and_parent_fk(self) -> None:
        result = build_rows(_base_spec())
        self.assertEqual(len(result.rows["ObjectSub"]), 1)
        sub = result.rows["ObjectSub"][0]
        self.assertEqual(sub["ObjectSubName"], "Invoice lines")
        self.assertEqual(sub["ObjectSubCode"], "invoice_lines")
        self.assertEqual(sub["ObjectSubWidth"], 80)
        self.assertEqual(len(result.rows["ObjectSubLine"]), 1)
        subline = result.rows["ObjectSubLine"][0]
        self.assertEqual(subline["ObjectSubLineCode"], "DESC")
        self.assertEqual(subline["ObjectSubLineTypeID"], 3)
        self.assertEqual(subline["ObjectSubID"], sub["ObjectSubID"])
        parent = next(r for r in result.rows["ObjectLine"] if r["ObjectLineCode"] == "LINES")
        self.assertEqual(parent["ObjectLineTypeID"], 5)
        self.assertEqual(parent["ObjectSubID"], sub["ObjectSubID"])
        self.assertNotIn("ObjectLineSlot", parent)
        oda = result.rows.get("ObjectDefaultAccess") or []
        col_oda = [
            r
            for r in oda
            if r.get("ObjectLineID") == parent["ObjectLineID"] and r.get("ObjectSubLineID")
        ]
        self.assertEqual(len(col_oda), 1)
        self.assertEqual(col_oda[0]["ObjectSubLineID"], subline["ObjectSubLineID"])
        self.assertEqual(col_oda[0]["ObjectLineIsEditableCreate"], 1)
        self.assertEqual(col_oda[0]["ObjectLineIsVisibleCreate"], 1)
        edges = {
            (e["TableName"], e["ChildTableName"], e["ChildTableRowID"]) for e in result.edges
        }
        self.assertIn(("ObjectLine", "ObjectSub", sub["ObjectSubID"]), edges)
        self.assertIn(("ObjectSub", "ObjectSubLine", subline["ObjectSubLineID"]), edges)
        default = result.rows["ObjectSubDefault"][0]
        self.assertEqual(default["ObjectSubDefaultIsDefault"], 1)
        dl = result.rows["ObjectSubDefaultLine"][0]
        self.assertEqual(dl["ObjectSubDefaultLineValidationID"], 1)
        title_tpl = next(
            r
            for r in result.rows["ObjectDefaultLine"]
            if r["ObjectLineID"]
            == next(x for x in result.rows["ObjectLine"] if x["ObjectLineCode"] == "LINES")[
                "ObjectLineID"
            ]
        )
        self.assertEqual(title_tpl["ObjectSubDefaultID"], default["ObjectSubDefaultID"])
        self.assertEqual(subline["ObjectSubLineOnGridIsAllowed"], 1)
        self.assertEqual(subline["ObjectSubLineIsSearch"], 1)
        og_rows = result.rows.get("ObjectSubLineOnGrid") or []
        self.assertEqual(len(og_rows), 1)
        self.assertEqual(og_rows[0]["ObjectSubLineID"], subline["ObjectSubLineID"])
        self.assertEqual(og_rows[0]["ObjectSubLineOnGridSize"], "Large")
        self.assertEqual(og_rows[0]["ObjectSubLineOnGridLength"], 100)
        self.assertIn(("ObjectSubLine", "ObjectSubLineOnGrid", og_rows[0]["ObjectSubLineOnGridID"]), edges)

    def test_object_sub_id_alias_does_not_emit_tree(self) -> None:
        spec = _base_spec()
        del spec["subgrids"]
        spec["layout"]["tabs"][0]["sections"][0]["fields"][1].pop("objectSub")
        spec["layout"]["tabs"][0]["sections"][0]["fields"][1]["objectSubId"] = 4242
        spec["templates"][0]["fields"] = {}
        result = build_rows(spec)
        self.assertNotIn("ObjectSub", result.rows)
        parent = next(r for r in result.rows["ObjectLine"] if r["ObjectLineCode"] == "LINES")
        self.assertEqual(parent["ObjectSubID"], 4242)

    def test_unknown_object_sub_key_raises(self) -> None:
        spec = _base_spec()
        spec["layout"]["tabs"][0]["sections"][0]["fields"][1]["objectSub"] = "missing"
        with self.assertRaises(ValueError) as ctx:
            build_rows(spec)
        self.assertIn("not in spec subgrids", str(ctx.exception))

    def test_number_requires_precision(self) -> None:
        spec = _base_spec()
        spec["subgrids"]["invoice_lines"]["layout"]["tabs"][0]["sections"][0]["fields"].append(
            {
                "name": "Qty",
                "code": "QTY",
                "type": "number",
                "slot": 2,
                "width": 20,
                "order": 20,
            }
        )
        with self.assertRaises(ValueError) as ctx:
            build_rows(spec)
        self.assertIn("requires precision", str(ctx.exception))

    def test_number_emits_precision(self) -> None:
        spec = _base_spec()
        spec["subgrids"]["invoice_lines"]["layout"]["tabs"][0]["sections"][0]["fields"].append(
            {
                "name": "Qty",
                "code": "QTY",
                "type": "number",
                "slot": 2,
                "width": 20,
                "order": 20,
                "precision": 0,
            }
        )
        result = build_rows(spec)
        qty = next(r for r in result.rows["ObjectSubLine"] if r["ObjectSubLineCode"] == "QTY")
        self.assertEqual(qty["ObjectSubLineNumberPrecision"], 0)
        self.assertEqual(qty["ObjectSubLineSlot"], 2)
        self.assertEqual(qty["ObjectSubLineIsEditable"], 1)

    def test_rejects_unsupported_types(self) -> None:
        for ftype in ("button", "report", "subgrid"):
            spec = _base_spec()
            spec["subgrids"]["invoice_lines"]["layout"]["tabs"][0]["sections"][0]["fields"][0][
                "type"
            ] = ftype
            with self.assertRaises(ValueError) as ctx:
                build_rows(spec)
            self.assertIn("not on ObjectSubLineType", str(ctx.exception))

    def test_combo_requires_reference(self) -> None:
        spec = _base_spec()
        spec["subgrids"]["invoice_lines"]["layout"]["tabs"][0]["sections"][0]["fields"].append(
            {
                "name": "Kind",
                "code": "KIND",
                "type": "combobox",
                "slot": 3,
                "width": 50,
                "order": 30,
            }
        )
        with self.assertRaises(ValueError) as ctx:
            build_rows(spec)
        self.assertIn("requires reference", str(ctx.exception))

    def test_combo_emits_source_id(self) -> None:
        spec = _base_spec()
        spec["references"] = {
            "ks_kind": {
                "name": "Kind",
                "typeId": 1,
                "styleId": 4,
                "values": [
                    {"value": "demo", "label": "Demo"},
                    {"value": "full", "label": "Full"},
                ],
            }
        }
        spec["subgrids"]["invoice_lines"]["layout"]["tabs"][0]["sections"][0]["fields"].append(
            {
                "name": "Kind",
                "code": "KIND",
                "type": "combobox",
                "slot": 3,
                "width": 50,
                "order": 30,
                "reference": {"reference": "ks_kind"},
            }
        )
        result = build_rows(spec)
        kind = next(r for r in result.rows["ObjectSubLine"] if r["ObjectSubLineCode"] == "KIND")
        source = result.rows["ObjectLineSource"][0]
        self.assertEqual(kind["ObjectSubLineTypeID"], 1)
        self.assertEqual(kind["ObjectSubLineSourceID"], source["ObjectLineSourceID"])
        self.assertIn(
            (
                "ObjectSubLine",
                "ObjectLineSource",
                source["ObjectLineSourceID"],
            ),
            {
                (e["TableName"], e["ChildTableName"], e["ChildTableRowID"])
                for e in result.edges
            },
        )


    def test_lookup_client_calc_and_language_table(self) -> None:
        spec = _base_spec()
        spec["references"] = {
            "ks_kind": {
                "name": "Kind",
                "typeId": 1,
                "styleId": 4,
                "values": [
                    {"value": "demo", "label": "Demo"},
                    {"value": "full", "label": "Full"},
                ],
            }
        }
        spec["lookups"] = {
            "kind_flag": {
                "name": "Kind flag",
                "values": [
                    {"source": "demo", "return": "N"},
                    {"source": "full", "return": "Y"},
                ],
            }
        }
        fields = spec["subgrids"]["invoice_lines"]["layout"]["tabs"][0]["sections"][0]["fields"]
        fields.extend(
            [
                {
                    "name": "Qty",
                    "code": "QTY",
                    "type": "number",
                    "slot": 2,
                    "width": 100,
                    "order": 20,
                    "precision": 0,
                },
                {
                    "name": "Amount",
                    "code": "AMOUNT",
                    "type": "number",
                    "slot": 3,
                    "width": 100,
                    "order": 30,
                    "precision": 2,
                },
                {
                    "name": "Total",
                    "code": "TOTAL",
                    "type": "number",
                    "slot": 4,
                    "width": 100,
                    "order": 40,
                    "precision": 2,
                },
                {
                    "name": "Kind",
                    "code": "KIND",
                    "type": "combobox",
                    "slot": 5,
                    "width": 100,
                    "order": 50,
                    "reference": {"reference": "ks_kind"},
                },
                {
                    "name": "Flag",
                    "code": "FLAG",
                    "type": "text",
                    "slot": 6,
                    "width": 100,
                    "order": 60,
                    "lookup": {"lookup": "kind_flag", "sourceField": "KIND"},
                },
            ]
        )
        spec["subgrids"]["invoice_lines"]["templates"][0]["fields"]["TOTAL"] = {
            "alwaysDisabled": True,
            "clientCalculation": {"type": "math", "expr": "id{QTY} * id{AMOUNT}"},
        }
        spec["languageTable"] = {
            "subgrids": {
                "invoice_lines": {
                    "tabs": {"General": {"cs": "Obecné"}},
                    "sections": {"General/Details": {"cs": "Podrobnosti"}},
                    "lines": {"DESC": {"cs": "Popis"}},
                    "templateHints": {"default": {"DESC": {"cs": "Popis položky"}}},
                }
            }
        }
        result = build_rows(spec)
        flag_dl = next(
            r
            for r in result.rows["ObjectSubDefaultLine"]
            if r["ObjectSubLineID"]
            == next(x for x in result.rows["ObjectSubLine"] if x["ObjectSubLineCode"] == "FLAG")[
                "ObjectSubLineID"
            ]
        )
        lookup = result.rows["ObjectLineLookup"][0]
        kind = next(r for r in result.rows["ObjectSubLine"] if r["ObjectSubLineCode"] == "KIND")
        self.assertEqual(flag_dl["ObjectSubDefaultLineLookupID"], lookup["ObjectLineLookupID"])
        self.assertEqual(flag_dl["ObjectSubDefaultLineLookupObjectSubLineID"], kind["ObjectSubLineID"])
        total_dl = next(
            r
            for r in result.rows["ObjectSubDefaultLine"]
            if r["ObjectSubLineID"]
            == next(x for x in result.rows["ObjectSubLine"] if x["ObjectSubLineCode"] == "TOTAL")[
                "ObjectSubLineID"
            ]
        )
        qty = next(r for r in result.rows["ObjectSubLine"] if r["ObjectSubLineCode"] == "QTY")
        amount = next(r for r in result.rows["ObjectSubLine"] if r["ObjectSubLineCode"] == "AMOUNT")
        self.assertEqual(total_dl["ObjectSubDefaultLineClientCalculationTypeID"], 1)
        self.assertEqual(total_dl["ObjectSubDefaultLineIsDisabled"], 1)
        self.assertEqual(
            total_dl["ObjectSubDefaultLineClientCalculation"],
            f"id{qty['ObjectSubLineID']} * id{amount['ObjectSubLineID']}",
        )
        lt = result.rows["LanguageTable"]
        by_col = {(r["TableName"], r["ColumnName"], r["UserLanguageCode"]): r for r in lt}
        self.assertEqual(
            by_col[("ObjectSubLine", "ObjectSubLineName", "cs")]["LanguageTableData"], "Popis"
        )
        self.assertEqual(
            by_col[("ObjectSubLineTab", "ObjectSubLineTabName", "cs")]["LanguageTableData"],
            "Obecné",
        )


class SubgridRoundtripTests(unittest.TestCase):
    def test_extract_subgrids_and_parent_bind(self) -> None:
        spec = _base_spec()
        result = build_rows(spec)
        xml_bytes = build_object_transfer_xml(
            result.rows, dedupe_edges(result.edges), build_object_map(dedupe_edges(result.edges))
        )
        with tempfile.TemporaryDirectory() as tmp:
            xml_path = Path(tmp) / "ot.xml"
            xml_path.write_bytes(xml_bytes)
            extracted = extract_spec(xml_path)

        self.assertIn("subgrids", extracted)
        self.assertIn("invoice_lines", extracted["subgrids"])
        tree = extracted["subgrids"]["invoice_lines"]
        self.assertEqual(tree["name"], "Invoice lines")
        fields = tree["layout"]["tabs"][0]["sections"][0]["fields"]
        self.assertEqual(fields[0]["code"], "DESC")
        self.assertTrue(tree["templates"][0]["fields"]["DESC"]["mandatory"])
        layout_fields = {
            f["code"]: f
            for tab in extracted["layout"]["tabs"]
            for sec in tab["sections"]
            for f in sec["fields"]
        }
        self.assertEqual(layout_fields["LINES"]["objectSub"], "invoice_lines")
        self.assertNotIn("objectSubId", layout_fields["LINES"])
        templates = extracted.get("templates") or []
        self.assertTrue(templates)
        self.assertEqual(templates[0]["fields"]["LINES"]["subgridTemplate"], "default")
        self.assertIn("invoice_lines", extracted["ids"]["explicit"].get("subgrids") or {})
        og = tree.get("onGrid") or {}
        self.assertEqual(og["fields"]["DESC"]["allowed"], True)
        self.assertTrue(og["fields"]["DESC"]["isSearch"])
        self.assertEqual(og["layouts"][0]["placements"][0]["columns"][0]["field"], "DESC")
        self.assertIn("invoice_lines/Large/Grid/Items/DESC", extracted["ids"]["explicit"].get("subgridOnGrid") or {})

    def test_extract_roundtrip_precision_and_reference(self) -> None:
        spec = _base_spec()
        spec["references"] = {
            "ks_kind": {
                "name": "Kind",
                "typeId": 1,
                "styleId": 4,
                "values": [
                    {"value": "demo", "label": "Demo"},
                    {"value": "full", "label": "Full"},
                ],
            }
        }
        spec["subgrids"]["invoice_lines"]["layout"]["tabs"][0]["sections"][0]["fields"].extend(
            [
                {
                    "name": "Qty",
                    "code": "QTY",
                    "type": "number",
                    "slot": 2,
                    "width": 20,
                    "order": 20,
                    "precision": 2,
                },
                {
                    "name": "Kind",
                    "code": "KIND",
                    "type": "combobox",
                    "slot": 3,
                    "width": 50,
                    "order": 30,
                    "reference": {"reference": "ks_kind"},
                },
            ]
        )
        result = build_rows(spec)
        xml_bytes = build_object_transfer_xml(
            result.rows, dedupe_edges(result.edges), build_object_map(dedupe_edges(result.edges))
        )
        with tempfile.TemporaryDirectory() as tmp:
            xml_path = Path(tmp) / "ot.xml"
            xml_path.write_bytes(xml_bytes)
            extracted = extract_spec(xml_path)

        fields = {
            f["code"]: f
            for f in extracted["subgrids"]["invoice_lines"]["layout"]["tabs"][0]["sections"][0][
                "fields"
            ]
        }
        self.assertEqual(fields["QTY"]["precision"], 2)
        self.assertEqual(fields["KIND"]["type"], "combobox")
        self.assertIn("reference", fields["KIND"])
        ref_key = fields["KIND"]["reference"]["reference"]
        self.assertIn(ref_key, extracted["references"])
        self.assertEqual(extracted["references"][ref_key]["name"], "Kind")

    def test_extract_lookup_client_calc_and_language_table(self) -> None:
        spec = _base_spec()
        spec["references"] = {
            "ks_kind": {
                "name": "Kind",
                "typeId": 1,
                "styleId": 4,
                "values": [
                    {"value": "demo", "label": "Demo"},
                    {"value": "full", "label": "Full"},
                ],
            }
        }
        spec["lookups"] = {
            "kind_flag": {
                "name": "Kind flag",
                "values": [
                    {"source": "demo", "return": "N"},
                    {"source": "full", "return": "Y"},
                ],
            }
        }
        fields = spec["subgrids"]["invoice_lines"]["layout"]["tabs"][0]["sections"][0]["fields"]
        fields.extend(
            [
                {
                    "name": "Qty",
                    "code": "QTY",
                    "type": "number",
                    "slot": 2,
                    "width": 100,
                    "order": 20,
                    "precision": 0,
                },
                {
                    "name": "Amount",
                    "code": "AMOUNT",
                    "type": "number",
                    "slot": 3,
                    "width": 100,
                    "order": 30,
                    "precision": 2,
                },
                {
                    "name": "Total",
                    "code": "TOTAL",
                    "type": "number",
                    "slot": 4,
                    "width": 100,
                    "order": 40,
                    "precision": 2,
                },
                {
                    "name": "Kind",
                    "code": "KIND",
                    "type": "combobox",
                    "slot": 5,
                    "width": 100,
                    "order": 50,
                    "reference": {"reference": "ks_kind"},
                },
                {
                    "name": "Flag",
                    "code": "FLAG",
                    "type": "text",
                    "slot": 6,
                    "width": 100,
                    "order": 60,
                    "lookup": {"lookup": "kind_flag", "sourceField": "KIND"},
                },
            ]
        )
        spec["subgrids"]["invoice_lines"]["templates"][0]["fields"]["TOTAL"] = {
            "alwaysDisabled": True,
            "clientCalculation": {"type": "math", "expr": "id{QTY} * id{AMOUNT}"},
        }
        spec["languageTable"] = {
            "subgrids": {
                "invoice_lines": {
                    "lines": {"DESC": {"cs": "Popis"}},
                }
            }
        }
        result = build_rows(spec)
        xml_bytes = build_object_transfer_xml(
            result.rows, dedupe_edges(result.edges), build_object_map(dedupe_edges(result.edges))
        )
        with tempfile.TemporaryDirectory() as tmp:
            xml_path = Path(tmp) / "ot.xml"
            xml_path.write_bytes(xml_bytes)
            extracted = extract_spec(xml_path)

        tree = extracted["subgrids"]["invoice_lines"]
        by_code = {
            f["code"]: f
            for f in tree["layout"]["tabs"][0]["sections"][0]["fields"]
        }
        self.assertEqual(by_code["FLAG"]["lookup"]["sourceField"], "KIND")
        self.assertIn(by_code["FLAG"]["lookup"]["lookup"], extracted["lookups"])
        total_cfg = tree["templates"][0]["fields"]["TOTAL"]
        self.assertTrue(total_cfg["alwaysDisabled"])
        self.assertEqual(total_cfg["clientCalculation"]["type"], "math")
        self.assertEqual(total_cfg["clientCalculation"]["expr"], "id{QTY} * id{AMOUNT}")
        self.assertEqual(
            extracted["languageTable"]["subgrids"]["invoice_lines"]["lines"]["DESC"]["cs"],
            "Popis",
        )

    def test_default_width_is_80(self) -> None:
        spec = _base_spec()
        result = build_rows(spec)
        self.assertEqual(result.rows["ObjectSub"][0]["ObjectSubWidth"], 80)

    def test_explicit_width_is_honored(self) -> None:
        spec = _base_spec()
        spec["subgrids"]["invoice_lines"]["width"] = 100
        result = build_rows(spec)
        self.assertEqual(result.rows["ObjectSub"][0]["ObjectSubWidth"], 100)

    def test_parent_step_access_copies_to_columns(self) -> None:
        spec = _base_spec()
        spec["workflow"] = {
            "mode": "full",
            "name": "Invoice",
            "steps": [
                {
                    "name": "Draft",
                    "role": "requestor",
                    "status": "open",
                    "access": [{"field": "LINES", "editable": True}],
                    "actions": [],
                }
            ],
        }
        spec["roles"] = {"requestor": {"name": "Requestor", "isRequestor": True}}
        spec["statuses"] = {"open": {"name": "Open", "order": 10, "isCompleted": False}}
        result = build_rows(spec)
        wsa = result.rows.get("WorkflowStepAccess") or []
        parent = next(r for r in result.rows["ObjectLine"] if r["ObjectLineCode"] == "LINES")
        subline = result.rows["ObjectSubLine"][0]
        widget = [
            r
            for r in wsa
            if r["ObjectLineID"] == parent["ObjectLineID"] and not r.get("ObjectSubLineID")
        ]
        cols = [
            r
            for r in wsa
            if r["ObjectLineID"] == parent["ObjectLineID"] and r.get("ObjectSubLineID")
        ]
        self.assertEqual(len(widget), 1)
        self.assertEqual(widget[0]["WorkflowStepAccessIsEditable"], 1)
        self.assertEqual(len(cols), 1)
        self.assertEqual(cols[0]["ObjectSubLineID"], subline["ObjectSubLineID"])
        self.assertEqual(cols[0]["WorkflowStepAccessIsEditable"], 1)

    def test_subgrid_ongrid_rejects_system_line(self) -> None:
        spec = _base_spec()
        spec["subgrids"]["invoice_lines"]["onGrid"]["layouts"][0]["placements"][0]["columns"] = [
            {"systemLine": "status", "position": 0, "length": 100}
        ]
        with self.assertRaises(ValueError) as ctx:
            build_rows(spec)
        self.assertIn("no systemLine", str(ctx.exception))

    def test_write_spec_splits_yaml(self) -> None:
        spec = _base_spec()
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "obj"
            write_spec(spec, directory)
            self.assertTrue((directory / "spec" / "subgrids.yaml").is_file())
            loaded = load_spec(directory)
        self.assertIn("invoice_lines", loaded["subgrids"])
        self.assertEqual(loaded["subgrids"]["invoice_lines"]["code"], "invoice_lines")

    def test_subgrid_default_value_delay_confirm_filter(self) -> None:
        spec = _base_spec()
        spec["references"] = {
            "ks_kind": {
                "name": "Kind",
                "typeId": 1,
                "styleId": 4,
                "values": [
                    {"value": "demo", "label": "Demo"},
                    {"value": "full", "label": "Full"},
                ],
            }
        }
        spec["subgrids"]["invoice_lines"]["layout"]["tabs"][0]["sections"][0]["fields"].extend(
            [
                {
                    "name": "Kind",
                    "code": "KIND",
                    "type": "combobox",
                    "slot": 2,
                    "width": 50,
                    "order": 20,
                    "reference": {"reference": "ks_kind"},
                },
                {
                    "name": "Intro",
                    "code": "INTRO",
                    "type": "description_memo",
                    "width": 100,
                    "order": 30,
                },
            ]
        )
        spec["subgrids"]["invoice_lines"]["templates"][0]["fields"] = {
            "DESC": {
                "mandatory": True,
                "defaultValue": "line",
                "calcDelay": 600,
                "calcConfirm": True,
            },
            "KIND": {"defaultFilter": "demo"},
            "INTRO": {"defaultValue": "<p>Row intro</p>"},
        }
        result = build_rows(spec)
        by_code = {
            row["ObjectSubLineCode"]: row["ObjectSubLineID"]
            for row in result.rows["ObjectSubLine"]
        }
        dl = {
            row["ObjectSubLineID"]: row for row in result.rows["ObjectSubDefaultLine"]
        }
        desc = dl[by_code["DESC"]]
        self.assertEqual(desc["ObjectSubDefaultLineValue"], "line")
        self.assertEqual(desc["ObjectSubDefaultLineClientCalcDelay"], 600)
        self.assertEqual(desc["ObjectSubDefaultLineIsClientCalcConfirm"], 1)
        self.assertEqual(dl[by_code["KIND"]]["ObjectSubDefaultLineValueFilter"], "demo")
        self.assertEqual(
            dl[by_code["INTRO"]]["ObjectSubDefaultLineDescMemo"], "<p>Row intro</p>"
        )
        self.assertNotIn("ObjectSubDefaultLineValue", dl[by_code["INTRO"]])

        xml_bytes = build_object_transfer_xml(
            result.rows, dedupe_edges(result.edges), build_object_map(dedupe_edges(result.edges))
        )
        with tempfile.TemporaryDirectory() as tmp:
            xml_path = Path(tmp) / "ot.xml"
            xml_path.write_bytes(xml_bytes)
            extracted = extract_spec(xml_path)
        fields = extracted["subgrids"]["invoice_lines"]["templates"][0]["fields"]
        self.assertEqual(fields["DESC"]["defaultValue"], "line")
        self.assertEqual(fields["DESC"]["calcDelay"], 600)
        self.assertTrue(fields["DESC"]["calcConfirm"])
        self.assertEqual(fields["KIND"]["defaultFilter"], "demo")
        self.assertEqual(fields["INTRO"]["defaultValue"], "<p>Row intro</p>")

    def test_subgrid_reject_delay_on_combo(self) -> None:
        spec = _base_spec()
        spec["references"] = {
            "ks_kind": {
                "name": "Kind",
                "typeId": 1,
                "styleId": 4,
                "values": [{"value": "demo", "label": "Demo"}],
            }
        }
        spec["subgrids"]["invoice_lines"]["layout"]["tabs"][0]["sections"][0]["fields"].append(
            {
                "name": "Kind",
                "code": "KIND",
                "type": "combobox",
                "slot": 2,
                "width": 50,
                "order": 20,
                "reference": {"reference": "ks_kind"},
            }
        )
        spec["subgrids"]["invoice_lines"]["templates"][0]["fields"]["KIND"] = {
            "calcDelay": 500
        }
        with self.assertRaisesRegex(ValueError, "calcDelay"):
            build_rows(spec)


if __name__ == "__main__":
    unittest.main()
