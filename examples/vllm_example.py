"""vLLM (OpenAI-compatible server) + PromptAnalyzer.

Start a vLLM server:
    python -m vllm.entrypoints.openai.api_server --model meta-llama/Llama-3.1-8B-Instruct

Then run:
    pip install promptanalyzer openai
    python examples/vllm_example.py
"""

from openai import OpenAI

from promptanalyzer import track

# vLLM exposes an OpenAI-compatible endpoint.
client = OpenAI(base_url="http://localhost:8000/v1", api_key="not-needed")


@track("self-hosted", provider="vllm")
def generate(prompt: str) -> str:
    response = client.chat.completions.create(
        model="meta-llama/Llama-3.1-8B-Instruct",
        messages=[
            {"role": "system", "content": "You are a self-hosted assistant."},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    print(generate("Summarize the benefits of local-first software."))
