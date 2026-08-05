# Contributing to PromptAnalyzer

Thanks for your interest in improving PromptAnalyzer! 🎉

## Getting started

```bash
git clone https://github.com/obaidhsn/promptanalyzer
cd promptanalyzer
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Development workflow

```bash
pytest              # run the test suite
ruff check .        # lint
ruff format .       # format
mypy promptanalyzer # type-check
```

All four must pass before a PR is merged (CI enforces them).

## Guiding principles

PromptAnalyzer has one non-negotiable rule: **it must never crash or slow down a
user's application.** When contributing, keep these in mind:

1. **Fail safe.** Any code that runs inside `@track` must be wrapped so exceptions
   are logged and swallowed, never propagated to the caller.
2. **Local-first.** No feature may require a cloud account, Docker, or Node.
3. **Provider-agnostic core.** The core must not import a provider SDK. New
   provider support goes in `promptanalyzer/adapters/` and does duck-typed
   extraction.
4. **Type hints everywhere.** Public functions are fully annotated and mypy-clean.

## Adding a provider adapter

1. Create `promptanalyzer/adapters/<provider>.py` subclassing `Adapter` (or
   `OpenAIAdapter` if the response is OpenAI-shaped).
2. Implement `matches`, `from_call`, and `from_response`, returning a
   `NormalizedRecord`. Never raise — return `None` fields on failure.
3. Register it in `promptanalyzer/adapters/__init__.py` (`REGISTRY` and, if it
   should auto-detect, `_DETECTION_ORDER`).
4. Add a test in `tests/test_adapters.py` and an example in `examples/`.

## Pull requests

- Keep PRs focused and small where possible.
- Add or update tests for any behaviour change.
- Update `CHANGELOG.md` under "Unreleased".
- Describe the motivation and any trade-offs in the PR body.

## Reporting bugs / requesting features

Open an issue using the templates in `.github/ISSUE_TEMPLATE/`. Include your
Python version, `promptanalyzer doctor` output, and a minimal reproduction.

## Code of Conduct

Be kind and respectful. We follow the
[Contributor Covenant](https://www.contributor-covenant.org/).
