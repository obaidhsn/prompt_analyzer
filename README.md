<div align="center">

# 🧬 PromptAnalyzer

### Git for prompts — local-first LLM observability & prompt versioning

**One decorator. Zero config. No Docker, no cloud, no npm.**

[![CI](https://github.com/obaidhsn/promptanalyzer/actions/workflows/tests.yml/badge.svg)](https://github.com/obaidhsn/promptanalyzer/actions/workflows/tests.yml)
[![PyPI](https://img.shields.io/pypi/v/promptanalyzer.svg)](https://pypi.org/project/promptanalyzer/)
[![Python](https://img.shields.io/pypi/pyversions/promptanalyzer.svg)](https://pypi.org/project/promptanalyzer/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

</div>

---

PromptAnalyzer gives any LLM-powered Python function automatic **prompt versioning**,
**inference logging**, **token & cost tracking**, and a **local dashboard** — by adding
a single `@track` decorator. Everything runs on your machine against SQLite. Nothing
leaves your laptop.

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

## ✨ Features

| | |
|---|---|
| 🔖 **Prompt versioning** | Every system prompt is SHA-256 hashed and versioned automatically — like Git commits for prompts. |
| 🧾 **Full inference logs** | User input, system prompt, response, model, provider, timing — all captured. |
| ⚡ **Zero overhead** | Sub-millisecond hot path; writes happen on a background thread. |
| 💸 **Token & cost tracking** | Built-in pricing for OpenAI, Anthropic, Google, Mistral, Groq and more. |
| 🔌 **Provider agnostic** | Auto-detects OpenAI, Claude, Gemini, Ollama, vLLM, LiteLLM, OpenRouter, Groq, Mistral, Azure — or bring your own. |
| 🪝 **Auto-instrumentation** | Captures the real request & response from the SDK call inside your function — even if you only return the answer string. |
| 📊 **Local dashboard** | Server-side rendered (FastAPI + HTMX + Alpine). No React, no build step. |
| 🔍 **Search & diff** | Full-text search across prompts/responses and GitHub-style version diffs. |
| 🛟 **Never crashes your app** | Logging failures are swallowed and logged — your application keeps running. |

## 🚀 Quick start

```bash
pip install "promptanalyzer[dashboard]"
```

1. **Decorate** an LLM function with `@track("project-name")`.
2. **Run** your application as usual.
3. **Open** the dashboard:

```bash
promptanalyzer dashboard
# http://localhost:4001
```

That's it. PromptAnalyzer creates `~/.promptanalyzer/promptanalyzer.db` on first use.

### Advanced decorator

```python
@track(
    name="medical-assistant",
    tags=["production"],
    metadata={"team": "AI"},
)
def chatbot(message): ...
```

### Any library (generic adapter)

```python
@track(
    name="custom-model",
    system=lambda args, kwargs: kwargs["system"],
    user=lambda args, kwargs: kwargs["prompt"],
    response=lambda result: result,
)
def my_llm(system, prompt): ...
```

## 🖥️ Dashboard

![Overview](docs/overview.svg)

![Diff viewer](docs/diff.svg)

| Overview | Prompt versions | Diff viewer | Run detail |
|---|---|---|---|
| Totals + runs/tokens/cost/latency charts | Every version with per-version metrics | GitHub-style added/removed lines | System prompt, messages, timing, tokens, cost |

> The images above are placeholders. To capture real screenshots, follow
> [`docs/screenshots.md`](docs/screenshots.md).

## 📚 Documentation

Full guides live in [`docs/`](docs/README.md): [Quickstart](docs/quickstart.md) ·
[Configuration](docs/configuration.md) · [Providers & adapters](docs/providers.md) ·
[Dashboard](docs/dashboard.md) · [CLI](docs/cli.md) ·
[Prompt versioning](docs/versioning.md) · [Database & migrations](docs/database.md) ·
[Performance](docs/performance.md) · [FAQ](docs/faq.md).

## 🔌 Supported providers

OpenAI · Anthropic Claude · Google Gemini · Ollama · vLLM · LiteLLM · OpenRouter ·
Groq · Mistral · Azure OpenAI · **any custom library** via the generic adapter.

See [`examples/`](examples/) for a runnable script per provider.

## ⚙️ Configuration

Zero config by default. Override via environment variables:

```env
PROMPTANALYZER_DB=sqlite
PROMPTANALYZER_SQLITE_PATH=~/.promptanalyzer/promptanalyzer.db
PROMPTANALYZER_DATABASE_URL=postgresql://user:password@localhost/dbname

PROMPTANALYZER_HOST=127.0.0.1
PROMPTANALYZER_PORT=4001

PROMPTANALYZER_AUTO_START=true      # start dashboard on import
PROMPTANALYZER_OPEN_BROWSER=true

PROMPTANALYZER_LOG_TOKENS=true
PROMPTANALYZER_LOG_COST=true
PROMPTANALYZER_SAVE_RESPONSES=true

PROMPTANALYZER_PROJECT=default
PROMPTANALYZER_ENV=development
```

**Priority:** decorator arguments → environment variables → defaults.
Legacy `PROMPTLOG_*` variables are also accepted.

## 🛠️ CLI

```bash
promptanalyzer init        # create ~/.promptanalyzer and the database
promptanalyzer dashboard   # launch the dashboard
promptanalyzer migrate     # create/upgrade the schema
promptanalyzer export csv  # export runs (json | csv | markdown)
promptanalyzer doctor      # diagnose your installation
promptanalyzer reset       # wipe all local data
```

## 🧱 Architecture

`@track` → adapter (normalizes any provider) → background writer → SQLite → FastAPI dashboard.
See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design.

## 🗺️ Roadmap

- [ ] OpenTelemetry export
- [ ] Prompt evaluation & A/B testing
- [ ] Dataset management & prompt playground
- [ ] Cloud sync + team collaboration
- [ ] Authentication & multi-user
- [ ] Plugin marketplace

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

## 📄 License

[MIT](LICENSE) © PromptAnalyzer Contributors
