# Quickstart

Get from zero to a working dashboard in about a minute.

## 1. Install

```bash
pip install "promptanalyzer[dashboard]"
```

The `[dashboard]` extra pulls in FastAPI, Uvicorn and Jinja2. If you only want to
capture runs (and view them later or on another machine), plain
`pip install promptanalyzer` is enough.

On first use, PromptAnalyzer creates:

```
~/.promptanalyzer/
    promptanalyzer.db     # SQLite database
    config                # reserved for future use
    logs/                 # reserved for future use
```

## 2. Add one decorator

```python
from promptanalyzer import track


@track("customer-support")
def chatbot(message):
    return client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a friendly support agent."},
            {"role": "user", "content": message},
        ],
    )
```

That's the whole integration. The decorator:

- detects the provider from the return value (OpenAI here),
- extracts the system prompt, user message, response, model, and token usage,
- versions the system prompt,
- estimates cost and latency,
- writes everything on a background thread so your function isn't slowed down.

## 3. Run your app

Run your application exactly as you normally would. Every decorated call is
recorded. If PromptAnalyzer's storage is ever unavailable, your app keeps running
— logging failures are swallowed and warned, never raised.

## 4. Open the dashboard

```bash
promptanalyzer dashboard
```

Open <http://localhost:4001>. You'll see totals, charts, projects, prompt
versions, diffs, run logs, and search.

## Advanced decorator

```python
@track(
    name="medical-assistant",
    tags=["production"],
    metadata={"team": "AI"},
    provider="anthropic",  # optional: force an adapter instead of auto-detecting
)
def chatbot(message): ...
```

## Async is supported

```python
@track("async-bot")
async def chat(message):
    return await client.chat.completions.create(...)
```

## Auto-start the dashboard from your app

Set an environment variable and the dashboard starts on import (non-blocking):

```bash
export PROMPTANALYZER_AUTO_START=true
export PROMPTANALYZER_OPEN_BROWSER=true
```

## Next steps

- [Track any library](providers.md#the-generic-adapter) with the generic adapter.
- [Configure storage](configuration.md), including PostgreSQL.
- [Export your data](cli.md#export) to JSON, CSV, or Markdown.
