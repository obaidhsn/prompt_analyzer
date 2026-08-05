# Database & migrations

## Schema

Three tables, heavily indexed to scale to 100,000+ runs.

### `projects`
| Column | Type | Notes |
|---|---|---|
| `id` | int PK | |
| `name` | str | unique, indexed |
| `created_at` | datetime | |

### `prompt_versions`
| Column | Type | Notes |
|---|---|---|
| `id` | int PK | |
| `project_id` | int FK → projects | indexed, cascade delete |
| `version` | int | per-project sequence |
| `hash` | str(64) | SHA-256, indexed |
| `system_prompt` | text | normalized |
| `created_at` | datetime | |

Unique constraint on `(project_id, hash)`; composite index on
`(project_id, version)`.

### `runs`
| Column | Type | Notes |
|---|---|---|
| `id` | int PK | |
| `project_id` | int FK → projects | indexed |
| `prompt_version_id` | int FK → prompt_versions | nullable |
| `function_name`, `provider`, `model` | str | `provider`, `model` indexed |
| `system_prompt`, `user_input`, `response` | text | |
| `latency_ms` | float | |
| `input_tokens`, `output_tokens`, `total_tokens` | int | |
| `cost` | float | |
| `tags`, `metadata` | JSON | |
| `error`, `env` | str/text | |
| `created_at` | datetime | indexed |

Composite index on `(project_id, created_at)` plus indexes on `model`,
`provider`, and `prompt_version_id` — covering the dashboard's filters and
sorts.

## SQLite (default)

The default backend is SQLite at `~/.promptanalyzer/promptanalyzer.db`. It runs in
**WAL mode** with `synchronous=NORMAL` and a `busy_timeout`, so the dashboard's
reads never block the background writer's writes.

## PostgreSQL

```env
PROMPTANALYZER_DB=postgres
PROMPTANALYZER_DATABASE_URL=postgresql://user:password@localhost:5432/promptanalyzer
```

```bash
pip install "promptanalyzer[postgres]"
promptanalyzer migrate
```

Connection pooling and pre-ping are enabled automatically for non-SQLite URLs.

## Migrations

For zero-config use, `promptanalyzer migrate` creates the schema with SQLAlchemy
`create_all`. For versioned migrations (recommended for shared PostgreSQL
deployments), an Alembic setup is bundled:

```bash
pip install "promptanalyzer[migrations]"

# apply the latest schema
alembic upgrade head

# after changing models, autogenerate a new revision
alembic revision --autogenerate -m "describe your change"
```

The Alembic environment (`promptanalyzer/migrations/env.py`) reads the same
`PROMPTANALYZER_*` configuration, so migrations target whatever database your app
uses. Batch mode is enabled for SQLite `ALTER` support.
