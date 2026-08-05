# Architecture

PromptAnalyzer is designed around one hard constraint: **it must never crash or
noticeably slow down the user's application.** Everything else follows from that.

## High-level flow

```
                    ┌────────────────────────────────────────────┐
   user function    │  @track decorator (tracker.py)             │
   ───────────────► │  1. run the wrapped function (timed)       │
                    │  2. pick an adapter (auto-detect / explicit)│
                    │  3. normalize call + response              │
                    │  4. estimate cost                          │
                    │  5. enqueue payload (non-blocking)         │
                    └───────────────┬────────────────────────────┘
                                    │  queue.put_nowait
                                    ▼
                    ┌────────────────────────────────────────────┐
                    │  BackgroundWriter (storage.py)             │
                    │  daemon thread drains the queue            │
                    │  - get/create Project                      │
                    │  - hash system prompt → get/create Version │
                    │  - insert Run                              │
                    └───────────────┬────────────────────────────┘
                                    ▼
                    ┌──────────────┐        ┌────────────────────┐
                    │  SQLite/PG   │◄───────│  FastAPI dashboard  │
                    │  (models.py) │  reads │  (server/, Jinja2)  │
                    └──────────────┘        └────────────────────┘
```

## Modules

| Module | Responsibility |
|---|---|
| `config.py` | Environment/default resolution. Dependency-light. |
| `tracker.py` | The `@track` decorator; sync + async; the safety boundary. |
| `adapters/` | Provider-specific extraction → `NormalizedRecord`. Registry + auto-detection. |
| `normalize.py` | The single normalized record every adapter produces. |
| `hashing.py` | Prompt normalization + SHA-256 hashing for versioning. |
| `pricing.py` | Token → USD estimation with prefix matching. |
| `models.py` | SQLAlchemy ORM: `Project`, `PromptVersion`, `Run`. |
| `db.py` | Engine/session lifecycle; SQLite WAL pragmas; pooling. |
| `storage.py` | Versioning logic + the background writer queue. |
| `queries.py` | Read-side analytics shared by the dashboard and exporter. |
| `exporter.py` | JSON / CSV / Markdown export. |
| `server/` | FastAPI app, Jinja2 templates, bundled static assets. |
| `cli.py` | `init`, `dashboard`, `migrate`, `export`, `doctor`, `reset`. |

## Design decisions

### Never break the caller
The wrapper runs the user's function first and always propagates its result or
exception. All PromptAnalyzer work happens in a `finally` block wrapped in
`try/except`; any internal error is logged at WARNING and swallowed. Storage
failures print `storage unavailable, continuing application execution`.

### Sub-millisecond overhead
The hot path only times the call, runs cheap extraction, and calls
`queue.put_nowait`. Database I/O is entirely on a daemon thread. If the queue is
full (default 10,000 items) the newest run is dropped rather than blocking.

### Provider agnosticism
The core never imports a provider SDK. Adapters do duck-typed extraction on the
returned object (`.choices`, `.content`, `.usage`, …), so PromptAnalyzer works
even for SDK versions it has never seen. Detection is ordered most-specific-first
with the OpenAI adapter as the broad fallback.

### Versioning = content-addressing
A prompt version is `(project, sha256(normalized_prompt))`. Identical prompts
reuse a version; any change mints the next integer version. This is Git's
content-addressed model applied to system prompts.

### Scaling to 100k+ runs
Composite indexes on `(project_id, created_at)`, plus `model`, `provider`, and
`prompt_version_id`. SQLite runs in WAL mode with `busy_timeout` so the dashboard
reads never block the writer. PostgreSQL is a drop-in via `PROMPTANALYZER_DATABASE_URL`.

## Extensibility (designed, not yet built)

The normalized record + adapter registry + background writer create clean seams for:
OpenTelemetry export (tap the writer), cloud sync (a second writer sink),
evaluation/A-B testing (new tables keyed on `prompt_version_id`), auth &
multi-user (a `User`/`Org` dimension on `Project`), and a plugin marketplace
(entry-point-registered adapters).
