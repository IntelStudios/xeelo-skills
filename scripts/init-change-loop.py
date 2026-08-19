#!/usr/bin/env python3
"""Create a change-loop folder under projects/<project>/changes/<slug>/."""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import date
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def _require_yaml():
    if yaml is None:
        raise SystemExit("PyYAML is required: pip install pyyaml")
    return yaml


def _latest_snapshot(project: Path) -> str | None:
    snap = project / "snapshots"
    if not snap.is_dir():
        return None
    dirs = sorted([p.name for p in snap.iterdir() if p.is_dir()])
    return dirs[-1] if dirs else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize a change loop directory")
    parser.add_argument(
        "--project",
        type=Path,
        required=True,
        help="Project directory (e.g. projects/ovnet)",
    )
    parser.add_argument(
        "--slug",
        required=True,
        help="Loop folder name, e.g. 20260811-loop-01-add-field",
    )
    parser.add_argument(
        "--objects",
        nargs="+",
        default=[],
        help="Object slugs under env/objects to copy into the loop",
    )
    parser.add_argument(
        "--tasks",
        default="",
        help="Optional initial tasks.md body",
    )
    args = parser.parse_args()

    project = args.project
    env_objects = project / "env" / "objects"
    loop_dir = project / "changes" / args.slug
    if loop_dir.exists():
        raise SystemExit(f"Change loop already exists: {loop_dir}")

    loop_dir.mkdir(parents=True)
    (loop_dir / "output").mkdir()
    objects_out = loop_dir / "objects"
    objects_out.mkdir()

    baseline = {
        "snapshot": _latest_snapshot(project),
        "createdAt": date.today().isoformat(),
        "objects": list(args.objects),
    }
    (loop_dir / "baseline.yaml").write_text(
        _require_yaml().safe_dump(baseline, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    tasks_body = args.tasks.strip() or (
        f"# Change loop: {args.slug}\n\n"
        "## Tasks\n\n"
        "- [ ] Describe the change\n"
    )
    (loop_dir / "tasks.md").write_text(tasks_body + "\n", encoding="utf-8")

    notes_body = (
        f"# Change loop: {args.slug}\n\n"
        "## Requested\n\n"
        "(what the user asked; prompt/plan excerpts OK — not the whole chat)\n\n"
        "## Done\n\n"
        "(what actually changed: objects, files, behaviour — not a raw diff)\n"
    )
    (loop_dir / "notes.md").write_text(notes_body, encoding="utf-8")

    copied = []
    for slug in args.objects:
        src = env_objects / slug
        if not src.is_dir():
            raise SystemExit(f"Object not found in env: {src}")
        dst = objects_out / slug
        shutil.copytree(src, dst)
        copied.append(slug)

    print(f"Created {loop_dir}")
    print(f"  baseline snapshot: {baseline['snapshot']}")
    print(f"  objects: {', '.join(copied) if copied else '(none yet)'}")


if __name__ == "__main__":
    main()
