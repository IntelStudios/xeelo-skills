---
name: ui-test
description: >-
  Drive Xeelo User UI in a browser: load site credentials, local login, create
  request, fill+save, workflow action, inbox. Use when the user invokes
  /ui-test, asks to UI-test a site, verify User UI after publish, or log in as
  a Xeelo user. Not Admin UI. Not GraphQL transfer (/download-db, /publish).
disable-model-invocation: true
---

# UI test (User UI)

Agent-driven checks of the **User UI** in a browser. Canonical files are this folder. Slash `/ui-test` is a pointer at [`.agents/skills/ui-test/SKILL.md`](../.agents/skills/ui-test/SKILL.md).

Not part of the publish loop. Do **not** run this after dry-run/`/publish` unless the user asks. Admin UI, Playwright, SSO, and MFA are out of scope.

Platform facts: [docs/ui-testing.md](../docs/ui-testing.md).

## Safety

- Never print, log, screenshot-caption, or put `userPwd` (or the GraphQL `token`) into chat, `notes.md`, or a shell command.
- Fill the password field from the connection file; do not echo it.
- On failure: describe what is on screen (labels, errors) **without** credentials.

## Inputs

Determine from the user message or ask once:

- **`<project>`** — slug under `projects/`. Default to the project in chat or the open `.xeelo-connection.json`.
- **What to verify** — smoke (login + inbox), create+save, workflow action, inbox row, or a named object from env/change-loop.

## Runtime

Same steps for both. Prefer the tools you have; do not invent a Playwright runner.

- **Local Cursor:** IDE browser — navigate, lock, snapshot, fill, click, unlock when finished.
- **Cloud agent:** computer-use / cloud browser, same procedure.

`projects/` and `.xeelo-connection.json` are gitignored. If the connection file is missing, **stop**. Tell the user to fill it in this workspace (or run locally). Do not ask them to paste `userPwd` into chat for storage.

## Procedure

Read the matching file **before** acting. Stop at the first blocker; do not skip ahead.

1. [connection.md](connection.md) — load JSON; require `userLogin` / `userPwd`.
2. [login/SKILL.md](login/SKILL.md) — local Sign in only. Stop on SSO/MFA ([reference/blockers.md](reference/blockers.md)).
3. Then only the flows the user asked for:
   - [create-request/SKILL.md](create-request/SKILL.md)
   - [fill-save/SKILL.md](fill-save/SKILL.md) + [reference/field-types.md](reference/field-types.md)
   - [workflow-action/SKILL.md](workflow-action/SKILL.md)
   - [inbox/SKILL.md](inbox/SKILL.md)

Smoke default (user said “UI test” with no object): connection → login → inbox/home visible.

## Report

Pass/fail per step. Failed step: visible text, URL path if known, screenshot if useful. Never include passwords.
