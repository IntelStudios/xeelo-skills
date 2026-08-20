#!/usr/bin/env python3
"""Extract Font Awesome 6.5.1 icon catalog from @intelstudios/font-awesome."""

from __future__ import annotations

import json
import os
from pathlib import Path

import yaml

USER_REPO = Path(os.environ.get("XEELO_USER_REPO", "/data/src/SmarterMDM-User"))
ADMIN_REPO = Path(os.environ.get("XEELO_ADMIN_REPO", "/data/src/SmarterMDM-Admin"))
PACKAGE_REL = Path("node_modules/@intelstudios/font-awesome")
USER_PACKAGE = USER_REPO / "GUI_src" / PACKAGE_REL
ADMIN_PACKAGE = ADMIN_REPO / "XeeloAdminNetGUI/ClientApp" / PACKAGE_REL
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "fontawesome-icons.json"

SPEC_STYLES = ("solid", "regular", "light", "thin", "brands")
PACKAGE_NAME = "@intelstudios/font-awesome"


def find_package() -> Path:
    for path in (USER_PACKAGE, ADMIN_PACKAGE):
        if (path / "fontawesome/metadata/icons.yml").is_file():
            return path
    raise SystemExit(
        "Could not find @intelstudios/font-awesome icons.yml "
        f"(tried {USER_PACKAGE} and {ADMIN_PACKAGE})"
    )


def parse_icons_yml(data: dict) -> list[dict]:
    icons: list[dict] = []
    for raw_id, meta in data.items():
        if not isinstance(meta, dict):
            continue
        icon_id = str(raw_id)
        styles = [s for s in (meta.get("styles") or []) if s in SPEC_STYLES]
        if not styles:
            continue
        aliases_raw = (meta.get("aliases") or {}).get("names") or []
        aliases = [str(a) for a in aliases_raw]
        terms = [str(t) for t in (meta.get("search") or {}).get("terms") or []]
        row: dict = {
            "id": icon_id,
            "label": str(meta.get("label") or icon_id),
            "styles": styles,
        }
        if aliases:
            row["aliases"] = aliases
        if terms:
            row["terms"] = terms
        icons.append(row)
    icons.sort(key=lambda row: row["id"])
    return icons


def main() -> None:
    package = find_package()
    pkg_json = json.loads((package / "package.json").read_text(encoding="utf-8"))
    version = str(pkg_json.get("version") or "")
    yml_path = package / "fontawesome/metadata/icons.yml"
    catalog = yaml.safe_load(yml_path.read_text(encoding="utf-8"))
    if not isinstance(catalog, dict):
        raise SystemExit(f"Unexpected icons.yml shape in {yml_path}")
    icons = parse_icons_yml(catalog)
    payload = {
        "version": version,
        "package": PACKAGE_NAME,
        "icons": icons,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUT_PATH.name} ({len(icons)} icons, version {version})")


if __name__ == "__main__":
    main()
