# UI testing (User UI)

Agent-driven checks of the **User UI** in a browser. Skills: [`ui_testing/`](../ui_testing/SKILL.md). Slash command: `/ui-test`.

This is **not** GraphQL, Object Transfer, Admin UI, Playwright, or CI. It is not in the publish loop — run it when the user asks.

## Connection

Same gitignored file as transfer: `projects/<project>/.xeelo-connection.json`.

| Field | GraphQL | User UI |
|-------|---------|---------|
| `xeeloUrl` | yes | yes — open this origin |
| `token` | yes (`isAdmin` for transfer) | unused |
| `userLogin` | unused | local username |
| `userPwd` | unused | local password |

`userLogin` / `userPwd` are optional. Empty or omitted: `/download-db` and `/publish` still work; `/ui-test` stops until they are set. Never copy `userPwd` between projects. Never print it.

Cloud agents often lack gitignored `projects/`. If the file is missing, run `/ui-test` in a workspace that has the connection filled in.

## Local login only

User UI sign-in is the site Sign-in form (username + password, **Sign me in**), not a GraphQL token. `/ui-test` uses that local form only. Microsoft/Entra, ADFS, OAuth, QR, SMS two-factor, TOTP, and MFA enrollment are **stop** conditions.

Unauthenticated User UI shows Sign in at the site root. Path `/login` is logout — do not start there.

## Lifecycle the skills cover

1. Load connection
2. Local login → User UI shell (`/xeelo` …)
3. **Create** (`Common.Create`) — `object.directCreate` skips the object picker on that object’s grid; several templates → Templates modal
4. Fill **text / number / combo** and header **Save** (`Common.Save`). Other field types: stop (see [`ui_testing/reference/field-types.md`](../ui_testing/reference/field-types.md))
5. Header **Workflow** → action tiles in a modal (not the inbox option wheel unless testing on-grid actions)
6. Inbox grid: find the row; optional on-grid workflow when `actions[].isOnGrid`

Save and Workflow live in the **request header**, not a form footer.

## Result video

Every `/ui-test` writes an MP4 (pass or fail). Screenshots + `manifest.json` + `result.mp4` live under `projects/<project>/ui-test/<stamp>/` (site copy, not the public KB git). No `userPwd` / `token` on slides. How to capture and render: [`ui_testing/report-video.md`](../ui_testing/report-video.md).
