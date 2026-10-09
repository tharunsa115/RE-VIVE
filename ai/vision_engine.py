import os
import mimetypes
from google import genai
from google.genai import types


def analyze_image(image_path: str, prompt: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing from environment variables."
        )

    if not os.path.isfile(image_path):
        raise FileNotFoundError(
            f"Image file not found: {image_path}"
        )

    mime_type, _ = mimetypes.guess_type(image_path)

    if not mime_type or not mime_type.startswith("image/"):
        mime_type = "image/jpeg"

    with open(image_path, "rb") as image_file:
        image_bytes = image_file.read()

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=[
            prompt,
            types.Part.from_bytes(
                data=image_bytes,
                mime_type=mime_type
            )
        ]
    )

    return (
        response.text or
        "Sorry, I couldn't analyze this image. Please try again."
    ).strip()


def assess_green_evidence(
    image_path: str,
    action_type: str,
    description: str
) -> str:
    prompt = f"""
You are the evidence assessment AI for RE:VIVE — Elementra.

The user claims to have completed this environmental action:
Action type: {action_type}
Description: {description}

Examine the uploaded image and return:

1. VISIBLE EVIDENCE: What can you actually see?
2. CLAIM CONSISTENCY: Does the image appear consistent with the claim?
3. LIMITATIONS: What cannot be proven from this image alone?
4. EVIDENCE STATUS: Choose CONSISTENT, PARTIAL, MISMATCH, or INSUFFICIENT.
5. NEXT STEPS: What additional evidence would help?

Be cautious and factual. A photo alone does not prove who performed
the action, when it happened, or the exact quantity recycled.
Never invent facts or claim independent verification.
"""
    return analyze_image(image_path, prompt)