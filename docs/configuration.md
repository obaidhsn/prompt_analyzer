# Configuration

PromptAnalyzer is **zero-config by default**. Everything below is optional.

## Precedence

Configuration is resolved in this order (highest wins):

1. **Decorator / call arguments** — e.g. `@track(name=..., provider=...)`.
2. **Environment variables** — `PROMPTANALYZER_*` (legacy `PROMPTLOG_*` also works).
3. **Built-in defaults**.

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `PROMPTANALYZER_HOME_DIR` | `~/.promptanalyzer` | Base directory for the DB, config, and logs. |
| `PROMPTANALYZER_DB` | `sqlite` | Backend: `sqlite` or `postgres`. |
| `PROMPTANALYZER_SQLITE_PATH` | `~/.promptanalyzer/promptanalyzer.db` | SQLite file path. |
| `PROMPTANALYZER_DATABASE_URL` | — | Full SQLAlchemy URL (required for Postgres). |
| `PROMPTANALYZER_HOST` | `127.0.0.1` | Dashboard bind host. |
| `PROMPTANALYZER_PORT` | `4001` | Dashboard port. |
| `PROMPTANALYZER_DASHBOARD` | `true` | Reserved flag for enabling the dashboard. |
| `PROMPTANALYZER_AUTO_START` | `false` | Start the dashboard on `import promptanalyzer`. |
| `PROMPTANALYZER_OPEN_BROWSER` | `false` | Open a browser when the dashboard starts. |
| `PROMPTANALYZER_LOG_TOKENS` | `true` | Persist token counts. |
| `PROMPTANALYZER_LOG_COST` | `true` | Estimate and persist cost. |
| `PROMPTANALYZER_SAVE_RESPONSES` | `true` | Persist prompt/response text (set `false` for privacy). |
| `PROMPTANALYZER_ENABLED` | `true` | Master switch; `false` disables all capture. |
| `PROMPTANALYZER_INSTRUMENT` | `true` | Auto-instrument SDK clients (OpenAI, Anthropic) to capture the real request/response. Set `false` to rely only on the decorated function's args and return value. |
| `PROMPTANALYZER_PROJECT` | `default` | Fallback project name when `@track` has none. |
| `PROMPTANALYZER_ENV` | `development` | Stored on each run (e.g. `production`, `staging`). |
| `PROMPTANALYZER_LOG_LEVEL` | `WARNING` | Internal logger verbosity. |

Booleans accept `1/true/yes/on` (case-insensitive).

## Example `.env`

```env
PROMPTANALYZER_DB=sqlite
PROMPTANALYZER_SQLITE_PATH=~/.promptanalyzer/promptanalyzer.db

PROMPTANALYZER_HOST=127.0.0.1
PROMPTANALYZER_PORT=4001

PROMPTANALYZER_AUTO_START=true
PROMPTANALYZER_OPEN_BROWSER=true

PROMPTANALYZER_LOG_TOKENS=true
PROMPTANALYZER_LOG_COST=true
PROMPTANALYZER_SAVE_RESPONSES=true

PROMPTANALYZER_PROJECT=default
PROMPTANALYZER_ENV=development
```

## PostgreSQL

```env
PROMPTANALYZER_DB=postgres
PROMPTANALYZER_DATABASE_URL=postgresql://user:password@localhost:5432/promptanalyzer
```

Install the driver:

```bash
pip install "promptanalyzer[postgres]"
```

## Privacy: don't store prompt text

If you only want metrics (latency, tokens, cost, versioning) without persisting
the actual prompts and responses:

```env
PROMPTANALYZER_SAVE_RESPONSES=false
```

Prompt **versioning still works** — the system prompt is hashed to derive its
version even when the text itself isn't stored on each run.

## Turn everything off

```env
PROMPTANALYZER_ENABLED=false
```

Decorated functions run untouched; nothing is captured. Useful for tests or
environments where you want the decorator to be a no-op.

## Custom pricing

Override or add model prices at runtime:

```python
from promptanalyzer import register_price

register_price("my-model", input_per_1k=0.001, output_per_1k=0.002)
```
