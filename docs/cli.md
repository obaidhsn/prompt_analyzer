# CLI reference

PromptAnalyzer installs two equivalent entry points: `promptanalyzer` and the
short alias `pa`.

```bash
promptanalyzer --help
promptanalyzer --version
```

## `init`

Create the home directory (`~/.promptanalyzer`) and the database.

```bash
promptanalyzer init
```

Idempotent — safe to run repeatedly.

## `dashboard`

Launch the local dashboard (blocking; `Ctrl+C` to stop).

```bash
promptanalyzer dashboard
promptanalyzer dashboard --host 0.0.0.0 --port 8080 --no-browser
```

| Flag | Description |
|---|---|
| `--host` | Bind host (default from config, `127.0.0.1`). |
| `--port` | Port (default `4001`). |
| `--no-browser` | Don't open a browser window. |

Requires the dashboard extra: `pip install "promptanalyzer[dashboard]"`.

## `migrate`

Ensure the database schema exists / is up to date.

```bash
promptanalyzer migrate
```

By default this uses SQLAlchemy `create_all` for zero-config setup. For advanced
or PostgreSQL workflows, Alembic is available — see [database.md](database.md).

## `export`

Export runs to `json`, `csv`, or `markdown`.

```bash
promptanalyzer export json
promptanalyzer export csv  --project medical-chatbot -o runs.csv
promptanalyzer export markdown --limit 100 -o report.md
```

| Argument / flag | Description |
|---|---|
| `format` | `json` (default), `csv`, `markdown`/`md`. |
| `--project` | Restrict to one project. |
| `--limit` | Max number of runs. |
| `-o, --output` | Write to a file instead of stdout. |

## `doctor`

Diagnose the installation and environment: version, Python, home directory,
database URL (credentials masked), dependency presence, and DB reachability.

```bash
promptanalyzer doctor
```

Exit code is non-zero if problems are found — useful in CI. Include its output
when filing a bug report.

## `reset`

Delete **all** stored data and recreate an empty schema.

```bash
promptanalyzer reset          # prompts for confirmation
promptanalyzer reset --yes    # skip the prompt (use with care)
```
