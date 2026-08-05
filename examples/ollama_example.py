"""Local Ollama models + PromptAnalyzer (fully offline, zero cost).

Run:
    pip install promptanalyzer ollama
    ollama pull llama3.1
    python examples/ollama_example.py
"""

import ollama

from promptanalyzer import track


@track("local-chatbot")
def chat(message: str) -> str:
    response = ollama.chat(
        model="llama3.1",
        messages=[
            {"role": "system", "content": "You are a helpful local assistant."},
            {"role": "user", "content": message},
        ],
    )
    return response["message"]["content"]


if __name__ == "__main__":
    print(chat("Explain WAL mode in SQLite in one sentence."))
