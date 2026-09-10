# UI testing blockers

Stop the `/ui-test` flow. Do not complete SSO or MFA. Do not store extra secrets.

## No local login form

Local username/password is shown only when the site enables local application login (or the URL has `local=true`). Otherwise the page may show only:

- Microsoft / Entra (MSAL)
- ADFS
- OAuth
- QR code login

If the local username field is missing, stop. `/ui-test` does not click those providers.

## After local Sign in

Stop on:

- Two-factor / SMS (`TwoFactorAuthRequired`)
- TOTP / authenticator
- MFA enrollment
- Maintenance mode
- Session-expired banner that returns you to Sign in without a local form

## Connection

- Missing `projects/<project>/.xeelo-connection.json` (common on cloud agents — gitignored)
- Empty `userLogin` / `userPwd`
- Asking the user to paste `userPwd` into chat

## Captcha / human gates

If a captcha or similar appears, stop and hand over to the user. Do not brute-force credentials.
