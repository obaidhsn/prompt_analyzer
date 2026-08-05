# Changelog

All notable changes to PromptAnalyzer are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Automatic client instrumentation** for OpenAI and Anthropic: `@track` now
  captures the real request (system/user prompts, model) and response (text,
  tokens, cost) from the SDK call *inside* the decorated function — even when the
  function returns only the answer string. Opt out with
  `PROMPTANALYZER_INSTRUMENT=false`.
- Positional function arguments are now bound by name for extractor fallback.

## [0.1.0] - 2026-08-04

### Added
- `@track` decorator for zero-config LLM observability (sync + async).
- Automatic **prompt versioning** via SHA-256 content hashing.
- Provider adapters: OpenAI, Anthropic, Google Gemini, Ollama, vLLM, LiteLLM,
  OpenRouter, Groq, Mistral, Azure OpenAI, plus a generic/custom adapter.
- Normalized inference record shared across all providers.
- Token usage and USD cost estimation with per-model pricing.
- Non-blocking **background writer** so tracking adds sub-millisecond overhead.
- SQLite (default) and PostgreSQL storage with indexes for 100k+ runs.
- Local **dashboard** (FastAPI + Jinja2 + HTMX + Alpine.js + Chart.js): overview
  with charts, projects, prompt versions, GitHub-style diff viewer, run logs,
  run detail, and global search with filters.
- Export to JSON / CSV / Markdown (CLI and API).
- CLI: `init`, `dashboard`, `migrate`, `export`, `doctor`, `reset`.
- Full environment-variable configuration with `PROMPTANALYZER_*`
  (and legacy `PROMPTLOG_*`) support.
- Fail-safe design: logging failures never crash the host application.

[Unreleased]: https://github.com/promptanalyzer/promptanalyzer/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/promptanalyzer/promptanalyzer/releases/tag/v0.1.0
