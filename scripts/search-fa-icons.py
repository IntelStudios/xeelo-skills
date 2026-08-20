#!/usr/bin/env python3
"""Search the local Font Awesome 6.5.1 catalog shipped in Xeelo User GUI."""

from __future__ import annotations

import argparse
import json
import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "data" / "fontawesome-icons.json"
MAX_SPEC_LEN = 50
MAX_RESULTS = 20


def default_variant(styles: list[str]) -> str:
    if "brands" in styles and "solid" not in styles:
        return "brands"
    return "solid"


def spec_for(icon_id: str, styles: list[str]) -> str | None:
    spec = f"fa-{icon_id} fa-{default_variant(styles)} fa-fw"
    if len(spec) > MAX_SPEC_LEN:
        return None
    return spec


def _score_icon(icon: dict, query: str) -> int:
    q = query.lower().strip()
    if not q:
        return 0
    icon_id = str(icon.get("id") or "").lower()
    aliases = [str(a).lower() for a in icon.get("aliases") or []]
    label = str(icon.get("label") or "").lower()
    terms = [str(t).lower() for t in icon.get("terms") or []]
    if icon_id == q:
        return 1000
    if q in aliases:
        return 900
    if icon_id.startswith(q):
        return 800
    if any(a.startswith(q) for a in aliases):
        return 700
    if any(t == q for t in terms):
        return 600
    if label == q:
        return 550
    if q in icon_id:
        return 400
    if any(q in a for a in aliases):
        return 350
    if q in label:
        return 300
    if any(q in t for t in terms):
        return 200
    return 0


@lru_cache(maxsize=1)
def load_catalog(path: str | None = None) -> dict:
    catalog_path = Path(path) if path else CATALOG_PATH
    return json.loads(catalog_path.read_text(encoding="utf-8"))


def search_icons(query: str, catalog: dict | None = None) -> list[dict]:
    data = catalog if catalog is not None else load_catalog()
    scored: list[tuple[int, dict]] = []
    for icon in data.get("icons") or []:
        icon_id = icon.get("id")
        styles = list(icon.get("styles") or [])
        if not icon_id or not styles:
            continue
        score = _score_icon(icon, query)
        if score <= 0:
            continue
        spec = spec_for(str(icon_id), styles)
        if spec is None:
            continue
        scored.append(
            (
                score,
                {
                    "id": icon_id,
                    "variant": default_variant(styles),
                    "spec": spec,
                },
            )
        )
    scored.sort(key=lambda item: (-item[0], item[1]["id"]))
    return [row for _, row in scored[:MAX_RESULTS]]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search the local Font Awesome catalog for Xeelo spec "
        "object.icon / objectType.icon / company.icon"
    )
    parser.add_argument("--query", required=True, help="Search text, e.g. bank")
    args = parser.parse_args()
    results = search_icons(args.query)
    if not results:
        print("No icons found.", file=sys.stderr)
        raise SystemExit(1)
    for row in results:
        print(row["spec"])


if __name__ == "__main__":
    main()
