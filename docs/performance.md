# Performance & reliability

PromptAnalyzer has one non-negotiable rule: **it must never crash or noticeably
slow down your application.**

## The hot path (< 5 ms)

When a decorated function returns, PromptAnalyzer does only cheap work on the
calling thread:

1. Read a monotonic clock for latency.
2. Run the adapter's extraction (attribute/dict lookups — no I/O).
3. Estimate cost (a dict lookup).
4. `queue.put_nowait(payload)` — hand off to the background writer.

All database I/O happens on a **dedicated daemon thread**. Your request path never
waits for a disk write or a database lock.

```
your function ──▶ extract + enqueue (µs–ms) ──▶ return to caller
                                    │
                                    ▼ (separate thread)
                         Project / Version / Run writes
```

## Backpressure

The writer queue is bounded (default 10,000 items). If it fills — for example a
sudden burst far faster than disk can absorb — the **newest run is dropped** with
a warning rather than blocking your application. Protecting the app always wins.

## Fail-safe design

Every layer is wrapped so failures are logged, never raised past the decorator:

- Adapter extraction errors → that field is `None`, tracking continues.
- Generic extractor exceptions → swallowed per field.
- Storage/database errors → logged as
  `storage unavailable, continuing application execution`; your function's result
  is already returned.
- Even the background thread guards each item so one bad write can't kill the writer.

If the wrapped function raises, PromptAnalyzer records the error **and re-raises
the original exception unchanged** — your error handling is unaffected.

## Scaling

- Composite and single-column indexes cover the dashboard's filters and sorts.
- SQLite WAL mode lets reads and writes proceed concurrently.
- The design targets **100,000+ runs** on a laptop; move to PostgreSQL for larger
  shared deployments (see [database.md](database.md)).

## Flushing (tests / shutdown)

Writes are asynchronous, so in tests or scripts you may want to wait for the queue
to drain:

```python
from promptanalyzer.storage import get_writer

get_writer().flush(timeout=5.0)  # block until pending runs are persisted
```

An `atexit` hook drains and stops the writer on interpreter shutdown.

## Measuring overhead yourself

```python
import time
from promptanalyzer import track


@track("bench")
def noop():
    return {"choices": [{"message": {"content": "x"}}]}


N = 10_000
start = time.perf_counter()
for _ in range(N):
    noop()
per_call_ms = (time.perf_counter() - start) / N * 1000
print(f"{per_call_ms:.3f} ms/call decorator overhead")
```
