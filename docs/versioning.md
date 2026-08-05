# Prompt versioning

PromptAnalyzer treats system prompts like Git treats source: each distinct prompt
is **content-addressed** and gets an incrementing version number per project.

## How a version is created

For every tracked run with a system prompt:

1. **Normalize** the prompt — normalize line endings and strip trailing
   whitespace on each line and surrounding blank lines, so cosmetic edits don't
   create noise.
2. **Hash** the normalized text with SHA-256.
3. **Look up** the hash within the project.
4. If the hash **exists**, reuse that version.
5. If it's **new**, create the next integer version (`v1`, `v2`, …).

Version numbers are **per project**, so `medical-bot` and `resume-agent` each
have their own `v1`.

## Example

```
medical-bot

v1  "You are a doctor assistant"
v2  "You are a doctor assistant. Always provide citations."
v3  "You are a doctor assistant. Always provide citations and cite sources."
```

Running `v1` again later reuses `v1` — it does not create `v4`.

## What's stored

Each `PromptVersion` row holds:

| Field | Meaning |
|---|---|
| `project_id` | Owning project. |
| `version` | Per-project integer (1, 2, 3, …). |
| `hash` | SHA-256 of the normalized prompt. |
| `system_prompt` | The normalized prompt text. |
| `created_at` | When this version was first seen. |

Every `Run` links back to the `PromptVersion` it used, which is how the dashboard
computes per-version metrics (run count, average latency, average cost, tokens).

## Diffing

The dashboard's diff viewer (`/projects/{id}/diff`) renders a GitHub-style
side-by-side comparison of any two versions, highlighting added, removed, and
changed lines. It's rendered server-side and needs no JavaScript.

## Runs without a system prompt

If a run has no system prompt (empty or `None`), no version is created — the run
is still recorded, just without a `prompt_version` link.

## Privacy note

If `PROMPTANALYZER_SAVE_RESPONSES=false`, per-run prompt/response text isn't
stored, but versioning still works: the prompt is hashed to resolve its version
even though the raw text isn't persisted on each run.
