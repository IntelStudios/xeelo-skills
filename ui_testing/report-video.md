# Result video

Every `/ui-test` **ends with a video**. Pass, fail, smoke, or stop on a blocker — still write the MP4. Chat text is not a substitute.

## Capture while testing

After each step that ran (or the step that stopped the flow), take a **screenshot**. Save under the site, not the public KB:

```text
projects/<project>/ui-test/<stamp>/
  01-login.png
  02-inbox.png
  …
  manifest.json
  result.mp4
```

`<stamp>` = `YYYYMMDD-HHMM` plus object slug or `smoke` (`20260910-1032-task`).

Do **not** screenshot a password field with a visible value. Do **not** put `userPwd` or GraphQL `token` on slides, in `manifest.json`, or in the filename.

## Manifesto

`manifest.json` next to the screenshots:

```json
{
  "title": "UI test Xeelo User UI",
  "subtitle": "<project> · <object> · <company> · <date>",
  "overall": "FAIL",
  "note": "Short reason for overall FAIL/PARTIAL. No secrets.",
  "steps": [
    {
      "label": "Login",
      "status": "PASS",
      "detail": "Inbox after local Sign in",
      "screenshot": "01-login.png"
    }
  ]
}
```

`status` / `overall`: `PASS` | `FAIL` | `PARTIAL` | `SKIP`. Omit `screenshot` when there is no frame (step still appears as a text slide).

## Render

From repo root (`.venv/bin/python` when `.venv/` exists). If import fails: `pip install pillow imageio imageio-ffmpeg`.

```bash
$PYTHON ui_testing/scripts/make_ui_test_video.py \
  --manifest projects/<project>/ui-test/<stamp>/manifest.json \
  --out projects/<project>/ui-test/<stamp>/result.mp4
```

Then **open** the MP4 and put the path in the chat report. Site folder `projects/` stays out of the public KB git.

If the renderer cannot run (missing deps on a cloud agent), say so in one sentence and still keep the screenshots + `manifest.json`. Retry locally when possible.
