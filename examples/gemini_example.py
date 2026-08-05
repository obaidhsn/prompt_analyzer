"""Google Gemini + PromptAnalyzer.

Run:
    pip install promptanalyzer google-generativeai
    export GOOGLE_API_KEY=...
    python examples/gemini_example.py
"""

import google.generativeai as genai

from promptanalyzer import track

genai.configure()
model = genai.GenerativeModel(
    "gemini-1.5-flash",
    system_instruction="You are a concise research assistant.",
)


@track("research-assistant", provider="google")
def summarize(topic: str) -> str:
    response = model.generate_content(f"Give me three bullet points about {topic}.")
    return response.text


if __name__ == "__main__":
    print(summarize("retrieval augmented generation"))
