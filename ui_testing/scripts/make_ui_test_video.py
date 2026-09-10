#!/usr/bin/env python3
"""Build a /ui-test result MP4 from a JSON manifesto + screenshots.

Never put userPwd or GraphQL tokens in the JSON or on slides.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

W, H = 1920, 1080
FPS = 2
DEFAULT_SECONDS = {"title": 3, "step": 3, "shot": 4, "summary": 5}

BG = (18, 22, 28)
FG = (245, 247, 250)
MUTED = (160, 170, 182)
PASS = (46, 184, 92)
FAIL = (220, 68, 70)
PARTIAL = (232, 168, 56)
SKIP = (120, 130, 142)
ACCENT = (70, 140, 220)
STATUS_COLOR = {
    "PASS": PASS,
    "FAIL": FAIL,
    "PARTIAL": PARTIAL,
    "SKIP": SKIP,
}

FONT_CANDIDATES = (
    Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
)
BOLD_CANDIDATES = (
    Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
)


def _require_imaging():
    try:
        import imageio.v2 as imageio  # noqa: F401
        import numpy as np  # noqa: F401
        from PIL import Image, ImageDraw, ImageFont  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "UI-test videos need pillow, imageio, and imageio-ffmpeg. "
            "From repo root: .venv/bin/pip install pillow imageio imageio-ffmpeg"
        ) from exc


def _font_path(bold: bool) -> Path | None:
    for path in BOLD_CANDIDATES if bold else FONT_CANDIDATES:
        if path.is_file():
            return path
    if bold:
        return _font_path(False)
    return None


def font(size: int, bold: bool = False):
    from PIL import ImageFont

    path = _font_path(bold)
    if path:
        return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def new_slide():
    from PIL import Image

    return Image.new("RGB", (W, H), BG)


def normalize_status(raw: str) -> str:
    status = (raw or "SKIP").strip().upper()
    if status not in STATUS_COLOR:
        raise ValueError(f"status must be PASS, FAIL, PARTIAL, or SKIP, got {raw!r}")
    return status


def banner(img, title: str, status: str):
    from PIL import Image, ImageDraw

    color = STATUS_COLOR[status]
    canvas = new_slide()
    shot = img.convert("RGB")
    bar = 120
    max_h = H - bar - 40
    max_w = W - 80
    ratio = min(max_w / shot.width, max_h / shot.height, 1.0)
    nw, nh = max(1, int(shot.width * ratio)), max(1, int(shot.height * ratio))
    shot = shot.resize((nw, nh), Image.Resampling.LANCZOS)
    canvas.paste(shot, ((W - nw) // 2, bar + 20 + (max_h - nh) // 2))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, W, bar), fill=(12, 15, 20))
    draw.rectangle((0, 0, 12, bar), fill=color)
    draw.text((36, 28), title, font=font(36, True), fill=FG)
    tw = draw.textlength(status, font=font(32, True))
    draw.rounded_rectangle((W - tw - 80, 32, W - 36, 88), radius=8, fill=color)
    draw.text((W - tw - 58, 42), status, font=font(32, True), fill=(255, 255, 255))
    return canvas


def text_slide(heading: str, lines: list[tuple[str, tuple[int, int, int]]]):
    from PIL import ImageDraw

    canvas = new_slide()
    draw = ImageDraw.Draw(canvas)
    draw.text((80, 80), heading, font=font(56, True), fill=FG)
    y = 200
    for text, color in lines:
        draw.ellipse((80, y + 10, 108, y + 38), fill=color)
        draw.text((130, y), text, font=font(40), fill=FG)
        y += 78
    return canvas


def summary_slide(manifest: dict[str, Any]):
    from PIL import ImageDraw

    canvas = new_slide()
    draw = ImageDraw.Draw(canvas)
    draw.text((80, 64), manifest.get("title") or "/ui-test", font=font(56, True), fill=FG)
    subtitle = manifest.get("subtitle") or ""
    if subtitle:
        draw.text((80, 140), subtitle, font=font(28), fill=MUTED)
    steps = manifest.get("steps") or []
    y = 210
    draw.rectangle((80, y - 16, W - 80, min(H - 100, y + 72 * len(steps) + 8)), fill=(28, 33, 42))
    for step in steps:
        label = str(step.get("label") or "step")
        status = normalize_status(str(step.get("status") or "SKIP"))
        color = STATUS_COLOR[status]
        draw.text((120, y + 16), label[:70], font=font(32), fill=FG)
        tw = draw.textlength(status, font=font(28, True))
        draw.rounded_rectangle((W - 80 - tw - 48, y + 12, W - 100, y + 56), radius=8, fill=color)
        draw.text((W - 80 - tw - 32, y + 18), status, font=font(28, True), fill=(255, 255, 255))
        y += 72
        if y > H - 140:
            break
    note = manifest.get("note") or ""
    if note:
        draw.text((80, H - 80), note[:110], font=font(26), fill=MUTED)
    return canvas


def _step_lines(step: dict[str, Any]) -> list[tuple[str, tuple[int, int, int]]]:
    status = normalize_status(str(step.get("status") or "SKIP"))
    color = STATUS_COLOR[status]
    lines = [(str(step.get("label") or "step"), color)]
    detail = str(step.get("detail") or "").strip()
    if detail:
        lines.append((detail[:90], MUTED))
    return lines


def build_frames(manifest: dict[str, Any], base: Path):
    from PIL import Image

    frames = []
    durations: list[int] = []
    overall = normalize_status(str(manifest.get("overall") or "FAIL"))
    title_lines: list[tuple[str, tuple[int, int, int]]] = []
    if manifest.get("subtitle"):
        title_lines.append((str(manifest["subtitle"]), ACCENT))
    title_lines.append((f"Overall: {overall}", STATUS_COLOR[overall]))
    if manifest.get("note"):
        title_lines.append((str(manifest["note"])[:90], MUTED))
    frames.append(text_slide(str(manifest.get("title") or "UI test"), title_lines))
    durations.append(DEFAULT_SECONDS["title"])

    for index, step in enumerate(manifest.get("steps") or [], start=1):
        status = normalize_status(str(step.get("status") or "SKIP"))
        label = f"{index}. {step.get('label') or 'step'}"
        shot_rel = step.get("screenshot")
        shot_path = (base / shot_rel) if shot_rel else None
        if shot_path and shot_path.is_file():
            frames.append(banner(Image.open(shot_path), label, status))
            durations.append(DEFAULT_SECONDS["shot"])
        else:
            frames.append(text_slide(label, _step_lines(step)))
            durations.append(DEFAULT_SECONDS["step"])

    frames.append(summary_slide(manifest))
    durations.append(DEFAULT_SECONDS["summary"])
    return frames, durations


def write_mp4(frames, durations: list[int], out: Path) -> None:
    import imageio.v2 as imageio
    import numpy as np

    out.parent.mkdir(parents=True, exist_ok=True)
    writer = imageio.get_writer(
        out,
        fps=FPS,
        codec="libx264",
        quality=8,
        pixelformat="yuv420p",
        macro_block_size=1,
    )
    try:
        for img, seconds in zip(frames, durations, strict=True):
            arr = np.asarray(img.convert("RGB"))
            for _ in range(max(1, seconds * FPS)):
                writer.append_data(arr)
    finally:
        writer.close()


def load_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("manifest must be a JSON object")
    _assert_no_secret_keys(data)
    for step in data.get("steps") or []:
        normalize_status(str(step.get("status") or "SKIP"))
    if data.get("overall"):
        normalize_status(str(data["overall"]))
    return data


def _assert_no_secret_keys(obj: Any) -> None:
    forbidden = {"userpwd", "user_pwd", "password", "token"}
    if isinstance(obj, dict):
        for key, value in obj.items():
            if str(key).lower() in forbidden:
                raise ValueError(f"manifest must not contain {key}")
            _assert_no_secret_keys(value)
    elif isinstance(obj, list):
        for item in obj:
            _assert_no_secret_keys(item)


def main(argv: list[str] | None = None) -> int:
    _require_imaging()
    parser = argparse.ArgumentParser(description="Write a /ui-test result MP4")
    parser.add_argument("--manifest", required=True, type=Path, help="JSON manifesto (no secrets)")
    parser.add_argument("--out", required=True, type=Path, help="Output .mp4 path")
    args = parser.parse_args(argv)
    manifest = load_manifest(args.manifest)
    frames, durations = build_frames(manifest, args.manifest.parent)
    write_mp4(frames, durations, args.out)
    print(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
