"""Assemble Object transfer XML document (Xeelo multi-block UTF-16 format)."""

from __future__ import annotations

import xml.etree.ElementTree as ET

# Data table emission order (matches recipes/dependency-order.md + onGrid).
TABLE_ORDER = [
    "Company",
    "ObjectType",
    "Role",
    "RequestStatus",
    "Object",
    "ObjectLineTab",
    "ObjectLineSection",
    "ObjectLineSource",
    "ObjectLineSourceValue",
    "ObjectLineSourceRefObject",
    "ObjectLineLookup",
    "ObjectLineLookupValue",
    "ObjectLineAutoNumber",
    "ObjectLine",
    "ObjectLineOnGrid",
    "ObjectMessage",
    "ObjectMessageCondition",
    "ObjectAction",
    "ObjectActionParam",
    "ObjectActionCondition",
    "Periodic",
    "PeriodicCondition",
    "PeriodicAction",
    "PeriodicActionCondition",
    "PeriodicActionParam",
    "Scheduler",
    "SchedulerLine",
    "SchedulerLineParam",
    "Workflow",
    "WorkflowStep",
    "WorkflowStepAccess",
    "WorkflowStepAction",
    "WorkflowStepObjectAction",
    "ObjectDefault",
    "ObjectDefaultAccess",
    "ObjectDefaultLine",
    "ObjectUpdateAction",
    "ObjectUpdateAccess",
    "ObjectUpdateActionCondition",
    "ObjectUpdateMessage",
    "LanguageTable",
    "TableComments",
]


def elem(name: str, value) -> ET.Element:
    node = ET.Element(name)
    node.text = "" if value is None else str(value)
    return node


def append_row(parent: ET.Element, table: str, row: dict) -> None:
    row_el = ET.SubElement(parent, table)
    for key, value in row.items():
        if value is not None:
            row_el.append(elem(key, value))


def _xmldata_fragment(*children: ET.Element) -> str:
    root = ET.Element("XMLData")
    for child in children:
        root.append(child)
    return ET.tostring(root, encoding="unicode")


def _sorted_tables(rows: dict[str, list[dict]]) -> list[str]:
    order_index = {name: idx for idx, name in enumerate(TABLE_ORDER)}
    return sorted(rows.keys(), key=lambda name: (order_index.get(name, len(TABLE_ORDER)), name))


def build_object_transfer_xml(
    rows: dict[str, list[dict]],
    edges: list[dict],
    object_map: list[dict],
    transfer_version: str = "1.3.0",
) -> bytes:
    fragments: list[str] = []

    setup_elements = []
    for edge in edges:
        setup = ET.Element("ObjectSetup")
        for key in ("TableName", "TableRowID", "ChildTableName", "ChildTableRowID"):
            setup.append(elem(key, edge[key]))
        setup_elements.append(setup)
    fragments.append(_xmldata_fragment(*setup_elements))

    map_elements = []
    for pair in object_map:
        omap = ET.Element("ObjectMap")
        omap.append(elem("TableName", pair["TableName"]))
        omap.append(elem("ChildTableName", pair["ChildTableName"]))
        map_elements.append(omap)
    fragments.append(_xmldata_fragment(*map_elements))

    transfer = ET.Element("TransferInfo")
    transfer.append(elem("TransferType", "OBJECT"))
    transfer.append(elem("Version", transfer_version))
    fragments.append(_xmldata_fragment(transfer))

    for table in _sorted_tables(rows):
        table_rows = rows[table]
        row_elements = []
        for row in table_rows:
            row_el = ET.Element(table)
            for key, value in row.items():
                if value is not None:
                    row_el.append(elem(key, value))
            row_elements.append(row_el)
        fragments.append(_xmldata_fragment(*row_elements))

    # Xeelo export: UTF-16 LE with BOM, no XML declaration, concatenated XMLData blocks.
    return "".join(fragments).encode("utf-16")
