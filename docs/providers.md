# Providers & adapters

PromptAnalyzer is **provider-agnostic**. The core never imports a provider SDK —
each adapter does defensive, duck-typed extraction on whatever object your
function returns and converts it into a single normalized record:

```python
{
    "provider": "openai",
    "model": "gpt-5",
    "system_prompt": "...",
    "user_prompt": "...",
    "response": "...",
    "input_tokens": 100,
    "output_tokens": 200,
    "latency_ms": 500,
    "cost": 0.01,
}
```

## Automatic instrumentation

A plain decorator can only see a function's arguments and return value. But most
real code builds the request **inside** the function and returns just the answer
text:

```python
@track("customer-support")
def answer(question: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a friendly support agent."},
            {"role": "user", "content": question},
        ],
    )
    return response.choices[0].message.content  # returns a string!
```

Here the messages and the response object never reach the decorator. To capture
them anyway, PromptAnalyzer **auto-instruments** the OpenAI and Anthropic clients:
while a tracked function runs, it records the real request (system/user prompts,
model) and response (text, tokens) directly from the SDK call. So the example
above logs the full prompt, response, model, tokens, **cost**, and a versioned
system prompt — with no code changes.

- Instrumentation is installed lazily the first time `@track` runs and is a no-op
  if the SDK isn't installed.
- Disable it with `PROMPTANALYZER_INSTRUMENT=false` to fall back to
  argument/return extraction only.
- It never changes the client's behaviour or return value — it only observes.

If you're on an unsupported client, either return the response object from your
function (so the adapter can read it) or use the
[generic adapter](#the-generic-adapter).

## Built-in adapters

| Provider | Auto-detected? | Notes |
|---|---|---|
| OpenAI | ✅ | Chat completions + legacy completions. |
| Anthropic Claude | ✅ | Messages API (`type == "message"`). |
| Google Gemini | ✅ | `google-generativeai` / `google-genai`. |
| Ollama | ✅ | Native client and OpenAI-compatible endpoint. |
| LiteLLM | ✅ | Normalizes to the OpenAI schema. |
| Groq | ✅ | OpenAI-compatible. |
| Mistral | ✅ | OpenAI-compatible. |
| Azure OpenAI | ✅* | Same shape as OpenAI. |
| OpenRouter | ✅* | Detected via namespaced model ids (`vendor/model`). |
| vLLM | via `provider="vllm"` | OpenAI-compatible self-hosted server. |
| Custom / any library | via extractors | See below. |

\* Auto-detected when a distinguishing signal is present; otherwise pass
`provider="azure"` / `provider="openrouter"` explicitly.

## Forcing an adapter

Auto-detection is convenient but you can always be explicit:

```python
@track("self-hosted", provider="vllm")
def generate(prompt): ...
```

## The generic adapter

When PromptAnalyzer doesn't ship a built-in adapter — or your client returns a
custom object — supply small extractor callables. Providing **any** of them
activates the generic adapter.

```python
@track(
    name="custom-model",
    provider="homegrown",  # label shown in the dashboard
    system=lambda args, kwargs: kwargs["system"],
    user=lambda args, kwargs: kwargs["prompt"],
    response=lambda result: result["text"],
    model=lambda args, kwargs, result: "my-model-v2",  # optional
)
def my_llm(system, prompt):
    return call_my_model(system=system, prompt=prompt)
```

Signatures:

| Extractor | Signature | Returns |
|---|---|---|
| `system` | `(args, kwargs) -> str \| None` | The system prompt. |
| `user` | `(args, kwargs) -> str \| None` | The user prompt. |
| `response` | `(result) -> str \| None` | The response text. |
| `model` | `(args, kwargs, result) -> str \| None` | The model name. |

Extractors are invoked defensively: if one raises, that field is simply `None`
and tracking continues. If a `usage` object is present on the result, token
counts are picked up automatically.

## Writing a new built-in adapter

1. Create `promptanalyzer/adapters/<provider>.py` subclassing `Adapter` (or
   `OpenAIAdapter` if the response is OpenAI-shaped).
2. Implement `matches`, `from_call`, and `from_response`, returning a
   `NormalizedRecord`. **Never raise** — return `None` fields on failure.
3. Register it in `promptanalyzer/adapters/__init__.py` (`REGISTRY`, and
   `_DETECTION_ORDER` if it should auto-detect).
4. Add a test and an example.

See [CONTRIBUTING.md](../CONTRIBUTING.md) for details, and the runnable
[`examples/`](../examples) directory for one script per provider.
