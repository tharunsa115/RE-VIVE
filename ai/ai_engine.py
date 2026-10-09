
import os
from google import genai


def ask_ai(prompt: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing from environment variables.")

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt
    )

    return (response.text or "Sorry, I couldn't generate a response.").strip()