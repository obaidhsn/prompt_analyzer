# Screenshots

The images in this folder illustrate the dashboard. The `*.svg` files are
lightweight placeholders; replace them with real captures for the polished look
in the top-level README.

## How to capture real screenshots

```bash
promptanalyzer init
python examples/openai_example.py     # or seed with your own app
promptanalyzer dashboard              # http://localhost:4001
```

Then capture each view at ~1280×800 and save alongside this file:

| File | View | URL |
|---|---|---|
| `overview.png` | Overview cards + charts | `/` |
| `projects.png` | Projects grid | `/projects` |
| `versions.png` | Prompt versions for a project | `/projects/1` |
| `diff.png` | Version diff viewer | `/projects/1/diff` |
| `runs.png` | Run logs table with filters | `/runs` |
| `run-detail.png` | Single run detail | `/runs/1` |

## Placeholders

- [`overview.svg`](overview.svg) — overview mock
- [`diff.svg`](diff.svg) — diff viewer mock
