# Dashboard

The dashboard is served by FastAPI with server-side-rendered Jinja2 templates.
HTMX powers partial updates (filtering, pagination), Alpine.js handles tiny
interactions, and Chart.js renders analytics. **There is no Node build step** —
all templates and static assets ship inside the Python package.

Start it:

```bash
promptanalyzer dashboard          # http://localhost:4001
promptanalyzer dashboard --port 8080 --no-browser
```

## Pages

### Overview (`/`)
Headline cards — projects, prompt versions, runs, tokens, estimated cost, average
latency — plus four 14-day charts: runs, token usage, cost, and average latency.
A "recent projects" table links into each project.

### Projects (`/projects`)
A card per project with its version count, run count, token total, and cost.

### Project detail (`/projects/{id}`)
Lists every **prompt version** (newest first) with a preview and per-version
metrics (runs, average latency, tokens, average cost, hash), plus recent runs.
A "Compare versions" button opens the diff viewer.

### Prompt version (`/versions/{id}`)
The full system prompt for one version, its creation date and hash, and aggregate
metrics: number of runs, average latency, average cost, total tokens. Includes the
runs that used this exact version.

### Diff viewer (`/projects/{id}/diff?a=&b=`)
A GitHub-style side-by-side diff of two prompt versions, rendered server-side (no
JavaScript required). Added, removed, and changed lines are highlighted. Pick any
two versions from the dropdowns.

### Run logs (`/runs`)
A paginated table of every inference: time, project, input, response, model,
latency, tokens, cost. Filter by model, provider, or free-text search — the table
updates in place via HTMX. Errored runs are flagged. Export buttons produce CSV/JSON.

### Run detail (`/runs/{id}`)
Everything captured for a single run: system prompt, user message, assistant
response, timing, token split, cost, tags, metadata, environment, and a link to
the prompt version it used.

### Search (`/search`)
Global full-text search across system prompts, user messages, and responses, with
model/provider filters.

## JSON API

The dashboard also exposes a small read API (handy for scripts and dashboards of
your own):

| Endpoint | Description |
|---|---|
| `GET /api/health` | Liveness + version. |
| `GET /api/stats` | Overview totals as JSON. |
| `GET /api/series?days=14` | Per-day runs/tokens/cost/latency series. |
| `GET /api/export?fmt=json\|csv\|markdown&project=` | Export runs. |
| `GET /api/docs` | Interactive OpenAPI docs (Swagger UI). |

## Offline behaviour

HTMX, Alpine.js, and Chart.js load from public CDNs. The dashboard **degrades
gracefully** without them — all pages, tables, and the diff viewer are fully
server-rendered; only live charts and in-place filtering need those scripts.
