# Connection for UI testing

Load `projects/<project>/.xeelo-connection.json` (gitignored). GraphQL scripts still need only `xeeloUrl` + `token`. UI testing also needs local User UI credentials.

```json
{
  "xeeloUrl": "https://<name>.xeelo.online/",
  "token": "",
  "userLogin": "",
  "userPwd": ""
}
```

| Field | Required for | Notes |
|-------|----------------|-------|
| `xeeloUrl` | GraphQL and UI | User UI origin. Open this URL, not `/graphql`. |
| `token` | GraphQL only | Not used to sign in to User UI. |
| `userLogin` | UI | Local username. Empty/omitted → stop. |
| `userPwd` | UI | Local password. Empty/omitted → stop. **Never print.** |

Python (password stays in the object; `repr` redacts it):

```python
from pathlib import Path
from scripts.ot_builder.graphql_client import ConnectionConfig

cfg = ConnectionConfig.load(Path("projects/<project>/.xeelo-connection.json"))
user_login, user_pwd = cfg.require_ui_login()
```

## Missing file or empty UI fields

Stop. Tell the user to add `userLogin` and `userPwd` in this workspace’s connection file. Cloud agents often cannot see gitignored `projects/` — then say to run `/ui-test` locally after filling the file.

Do **not**:

- Copy `userPwd` from another project
- Ask the user to paste the password into chat so you can store it
- Write a `.xeelo-connection.example.json` with a real password
