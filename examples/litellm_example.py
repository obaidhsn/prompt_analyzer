"""LiteLLM (any provider, one API) + PromptAnalyzer.

Run:
    pip install promptanalyzer litellm
    python examples/litellm_example.py
"""

import litellm

from promptanalyzer import track


@track("multi-provider", provider="litellm")
def ask(prompt: str, model: str = "gpt-4o-mini") -> str:
    response = litellm.completion(
        model=model,
        messages=[
            {"role": "system", "content": "Answer in one short sentence."},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    print(ask("What is prompt versioning?"))
