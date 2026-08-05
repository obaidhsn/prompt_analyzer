# PromptAnalyzer Documentation

Welcome to the PromptAnalyzer docs. PromptAnalyzer is **Git for prompts** — add one
decorator to any LLM function and get automatic prompt versioning, inference logs,
token & cost tracking, and a local dashboard. Local-first, zero-config, no cloud.

## Contents

| Guide | What it covers |
|---|---|
| [Quickstart](quickstart.md) | Install, add `@track`, open the dashboard in 60 seconds. |
| [Configuration](configuration.md) | Every `PROMPTANALYZER_*` variable and the precedence rules. |
| [Providers & adapters](providers.md) | Supported providers and how to track any custom library. |
| [Dashboard](dashboard.md) | A tour of every page and how the analytics are computed. |
| [CLI](cli.md) | `init`, `dashboard`, `migrate`, `export`, `doctor`, `reset`. |
| [Prompt versioning](versioning.md) | How versions are hashed, reused, and diffed. |
| [Database & migrations](database.md) | Schema, SQLite vs PostgreSQL, Alembic. |
| [Performance & reliability](performance.md) | The <5 ms hot path and fail-safe design. |
| [FAQ](faq.md) | Common questions and gotchas. |

## The 30-second version

```python
from promptanalyzer import track


@track("medical-chatbot")
def ask(message):
    return client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a doctor's assistant."},
            {"role": "user", "content": message},
        ],
    )
```

```bash
promptanalyzer dashboard   # → http://localhost:4001
```

## Screenshots

This folder is also where dashboard screenshots referenced by the top-level
[`README`](../README.md) live. To regenerate them locally:

```bash
promptanalyzer init
python examples/openai_example.py   # or any example / your own app
promptanalyzer dashboard
```

Then capture `http://localhost:4001` and save the images here as
`overview.png`, `versions.png`, `diff.png`, and `run-detail.png`. A
[`screenshots.md`](screenshots.md) checklist describes the exact views to grab.

See [ARCHITECTURE.md](../ARCHITECTURE.md) for the internal design.
