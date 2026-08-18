# Hooks

`pre-commit` runs two scanners, because they are blind in different places.
Measured on the same five planted secrets:

| planted | `secret_scan.py` | `gitleaks` |
|---|---|---|
| AWS key, documentation example | caught | skipped — known example value |
| AWS key, realistic | caught | caught (generic-api-key) |
| GitHub token | caught | caught (github-pat) |
| Slack bot token | missed | caught (slack-bot-token) |
| password inside a `postgres://` URL | caught *after this test* | missed |

The last row is the reason the table exists. Neither tool saw it until it
was planted on purpose, and a rule was added. Coverage that has not been
measured against a planted failure is a guess.

Enable them in a fresh clone:

    git config core.hooksPath tools/hooks

The client denylist is not in this repository. `secret_scan.py` looks for
it one directory above the repository root; see `tools/denylist.example.txt`.
