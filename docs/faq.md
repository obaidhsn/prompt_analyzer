# FAQ

### Does PromptAnalyzer send my prompts anywhere?
No. It's **local-first**. Everything is written to a local SQLite file
(`~/.promptanalyzer/promptanalyzer.db`) by default. No cloud account, no external
service, no telemetry.

### Will it slow down my app?
No. The decorator's hot path is microseconds-to-milliseconds; all database writes
happen on a background thread. See [performance.md](performance.md).

### What happens if the database is unavailable?
Your app keeps running. The failure is logged as
`storage unavailable, continuing application execution` and the run is dropped.
Logging never raises past the decorator.

### Do I need the dashboard installed to capture runs?
No. `pip install promptanalyzer` captures runs. The `[dashboard]` extra
(FastAPI/Uvicorn/Jinja2) is only needed to *view* them. You can capture on one
machine and open the DB on another.

### Does it work with async functions?
Yes. `@track` detects coroutine functions and wraps them appropriately.

### My function returns only the answer string — are prompts/tokens/cost still captured?
Yes. PromptAnalyzer auto-instruments the OpenAI and Anthropic clients, so it reads
the real request and response from the SDK call inside your function even when you
return just `response.choices[0].message.content`. See
[Automatic instrumentation](providers.md#automatic-instrumentation). If you're on
an unsupported client, return the response object or use the generic adapter.

### My provider isn't in the list. Can I still track it?
Yes — use the [generic adapter](providers.md#the-generic-adapter) with
`system=/user=/response=` extractor callables. Any Python LLM library can integrate.

### Auto-detection picked the wrong provider. What do I do?
Pass `provider="..."` explicitly to `@track`.

### How do I avoid storing sensitive prompt/response text?
Set `PROMPTANALYZER_SAVE_RESPONSES=false`. You keep metrics and prompt
*versioning* (via hashing) without persisting the raw text.

### Are token counts and costs always accurate?
Token counts come straight from the provider's `usage` object when available.
Costs are **estimates** from a built-in price table (per 1K tokens) and default to
`0` / `None` for unknown models. Override with
[`register_price`](configuration.md#custom-pricing).

### Can I use PostgreSQL?
Yes — set `PROMPTANALYZER_DATABASE_URL` and install
`pip install "promptanalyzer[postgres]"`. See [database.md](database.md).

### How do I export my data?
`promptanalyzer export json|csv|markdown` (see [cli.md](cli.md)) or
`GET /api/export` from the dashboard.

### How do I reset everything?
`promptanalyzer reset` (add `--yes` to skip confirmation). This drops all data and
recreates an empty schema.

### Which Python versions are supported?
Python 3.10+.

### Is it type-checked and tested?
Yes — the package is fully type-hinted, `mypy`-clean, `ruff`-formatted, and covered
by unit and integration tests run in CI across Python 3.10–3.13.
