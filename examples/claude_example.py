"""Anthropic Claude + PromptAnalyzer.

Run:
    pip install promptanalyzer anthropic
    export ANTHROPIC_API_KEY=sk-ant-...
    python examples/claude_example.py
"""

import anthropic

from promptanalyzer import track

client = anthropic.Anthropic()


@track("medical-assistant", tags=["production"], metadata={"team": "AI"})
def diagnose(symptom: str) -> str:
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=512,
        system="You are a careful medical assistant. Always recommend seeing a professional.",
        messages=[{"role": "user", "content": symptom}],
    )
    return message.content[0].text


if __name__ == "__main__":
    print(diagnose("I have a mild headache and feel tired."))
    print("\nRun `promptanalyzer dashboard` and open http://localhost:4001")
