
from ollama import chat


def analyze_image(image_path: str, prompt: str) -> str:
    response = chat(
        model="qwen2.5vl:7b",
        messages=[
            {
                "role": "user",
                "content": prompt,
                "images": [image_path]
            }
        ],
        options={
            "num_ctx": 8192
        }
    )



    return response["message"]["content"].strip()


def assess_green_evidence(image_path: str, action_type: str, description: str) -> str:
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
