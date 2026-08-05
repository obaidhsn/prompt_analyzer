"""OpenAI + PromptAnalyzer.

Run:
    pip install promptanalyzer openai python-dotenv
    export OPENAI_API_KEY=sk-...        # or put it in a .env file
    python examples/openai_example.py
    promptanalyzer dashboard            # open http://localhost:4001

Note: PromptAnalyzer auto-instruments the OpenAI client, so it captures the
system/user prompts, model, tokens and cost from the real request/response —
even though this function returns only the answer string.
"""

from dotenv import load_dotenv  # optional: load OPENAI_API_KEY from a .env file
from openai import OpenAI

from promptanalyzer import track

load_dotenv(override=True)
client = OpenAI()


@track("customer-support")
def answer(question: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a friendly support agent. Be concise."},
            {"role": "user", "content": question},
        ],
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    print(answer("How do I reset my password?"))
    print(answer("Where can I download my invoices?"))
    print("\nLogged. Run `promptanalyzer dashboard` and open http://localhost:4001")
