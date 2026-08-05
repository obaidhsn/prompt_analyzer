"""Track ANY library with the generic adapter.

When PromptAnalyzer doesn't ship a built-in adapter for your LLM library, supply
small extractor callables so tracking still captures prompts, responses and
(optionally) token usage.

Run:
    pip install promptanalyzer
    python examples/custom_adapter.py
"""

from promptanalyzer import track


class MyHomegrownLLM:
    """Pretend this is an in-house or unsupported client."""

    def complete(self, *, system: str, prompt: str) -> dict:
        return {"text": f"[echo] {prompt}", "usage": {"prompt_tokens": 5, "completion_tokens": 7}}


llm = MyHomegrownLLM()


@track(
    name="custom-model",
    provider="homegrown",
    system=lambda args, kwargs: kwargs["system"],
    user=lambda args, kwargs: kwargs["prompt"],
    response=lambda result: result["text"],
)
def run(system: str, prompt: str) -> dict:
    return llm.complete(system=system, prompt=prompt)


if __name__ == "__main__":
    run(system="You are terse.", prompt="Hello, world!")
    print("Tracked a custom-library call. Run `promptanalyzer dashboard`.")
