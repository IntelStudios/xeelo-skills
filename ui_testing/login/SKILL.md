---
name: ui-test-login
description: >-
  Sign in to Xeelo User UI with local username and password from
  .xeelo-connection.json. Use from /ui-test after loading connection. Stop on
  SSO, MFA, TOTP, or missing local login form.
disable-model-invocation: true
---

# Login (User UI)

Read [../connection.md](../connection.md) first. Blockers: [../reference/blockers.md](../reference/blockers.md).

User UI login is **not** GraphQL. Open `xeeloUrl` (site root). Unauthenticated User UI shows the Sign-in form. Path `/login` is logout, not the sign-in page — do not start there.

## Local form only

Proceed only when the **local** username + password form is visible (site has local application login, or the URL includes `local=true`).

- Username: text input `name="username"` (`autocomplete="username"`).
- Password: password control (`autocomplete="current-password"`).
- Submit: button **Sign me in** (`UserResources.SignMeIn`).
- Optional: Remember checkbox — leave as-is unless the user asked.

Fill `userLogin` into username. Fill `userPwd` into the password field **without echoing it**. Click Sign me in.

Do **not** tick through Microsoft/Entra, ADFS, OAuth, or QR login. If those are the only options, stop ([blockers](../reference/blockers.md)).

## After submit

**Success:** login form is gone; User UI shell is up (tree, inbox, dashboard, or tasks). Typical landing is `/xeelo` (home / dashboard / tasks). That is enough for smoke.

**Stop (do not complete MFA):**

- Red alert on the form (wrong credentials / general error)
- Two-factor / SMS code
- TOTP / authenticator code
- MFA enrollment modal
- Maintenance message

Report the visible error key or text. Never include the password.
