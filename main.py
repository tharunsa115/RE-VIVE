from image_processor import get_image_info
from pdf_processor import extract_text_from_pdf
from database import (
    save_interaction,
    init_db,
    save_green_action,
    get_green_stats,
    get_green_history
)
from ai.vision_engine import analyze_image, assess_green_evidence
import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ai.ai_engine import ask_ai

app = FastAPI(title="PROMPTVERSE AI")
@app.get("/dashboard")
def dashboard():
    return FileResponse("frontend/dashboard.html")

init_db()

# Serve frontend files
app.mount("/static", StaticFiles(directory="frontend"), name="static")


class PromptRequest(BaseModel):
    prompt: str
class DocumentRequest(BaseModel):
    text: str
    instruction: str


@app.get("/")
def home():
    return FileResponse("frontend/index.html")


@app.post("/ask")
def ask(request: PromptRequest):
    result = ask_ai(request.prompt)

    save_interaction(
        request.prompt,
        str(result)
    )

    return {
        "prompt": request.prompt,
        "result": result
    }
@app.post("/analyze-document")
def analyze_document(request: DocumentRequest):
    prompt = f"""
Analyze the following document according to the instruction.

Instruction:
{request.instruction}

Document:
{request.text}
"""

    result = ask_ai(prompt)

    return {
        "result": result
    }
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_path = os.path.join("uploads", file.filename)

    with open(file_path, "wb") as buffer:
        contents = await file.read()
        buffer.write(contents)

    result = {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": len(contents),
        "saved_to": file_path
    }

    if file.filename.lower().endswith(".pdf"):
        extracted_text = extract_text_from_pdf(file_path)

        result["extracted_text"] = extracted_text

        if extracted_text:
            analysis_prompt = f"""
Analyze this document and provide:

1. A short summary
2. The main points
3. Important information or conclusions

Document:
{extracted_text}
"""

            result["analysis"] = ask_ai(analysis_prompt)

    
    elif file.filename.lower().endswith(
        (".png", ".jpg", ".jpeg", ".webp")
    ):
        image_info = get_image_info(file_path)
        result["image_info"] = image_info

    return result

@app.post("/analyze-image")
async def analyze_image_file(
    file: UploadFile = File(...),
    instruction: str = "Identify the waste item, its likely material, the best reuse or disposal action, practical steps, environmental benefit, and confidence level. Do not only describe the image."
):
    file_path = os.path.join("uploads", file.filename)

    with open(file_path, "wb") as buffer:
        contents = await file.read()
        buffer.write(contents)

    result = analyze_image(file_path, instruction)

    return {
        "filename": file.filename,
        "instruction": instruction,
        "result": result

    }

from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone

GREEN_UPLOAD_DIR = Path("uploads/green_actions")
GREEN_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EVIDENCE = {
    ".jpg", ".jpeg", ".png", ".webp",
    ".mp4", ".webm", ".mov"
}

MAX_EVIDENCE_SIZE = 25 * 1024 * 1024


@app.post("/green-actions")
async def create_green_action(
    action_type: str = Form(...),
    description: str = Form(...),
    file: UploadFile = File(...),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None)
):
    action_type = action_type.strip()
    description = description.strip()

    if not action_type or len(action_type) > 100:
        raise HTTPException(400, "Enter a valid action type.")

    if not description or len(description) > 2000:
        raise HTTPException(400, "Description must be 1–2000 characters.")

    if (latitude is None) != (longitude is None):
        raise HTTPException(400, "Provide both GPS coordinates or neither.")

    if latitude is not None and not (-90 <= latitude <= 90):
        raise HTTPException(400, "Invalid latitude.")

    if longitude is not None and not (-180 <= longitude <= 180):
        raise HTTPException(400, "Invalid longitude.")

    extension = Path(file.filename or "").suffix.lower()

    if extension not in ALLOWED_EVIDENCE:
        raise HTTPException(
            400, "Upload a JPG, PNG, WEBP, MP4, WEBM, or MOV file."
        )

    saved_path = None

    try:
        contents = await file.read(MAX_EVIDENCE_SIZE + 1)

        if not contents:
            raise HTTPException(400, "The evidence file is empty.")

        if len(contents) > MAX_EVIDENCE_SIZE:
            raise HTTPException(413, "Maximum evidence size is 25 MB.")

        # Basic content checks for common image formats.
        signatures = {
            ".jpg": contents.startswith(b"\xff\xd8\xff"),
            ".jpeg": contents.startswith(b"\xff\xd8\xff"),
            ".png": contents.startswith(b"\x89PNG\r\n\x1a\n"),
            ".webp": (
                len(contents) >= 12
                and contents[:4] == b"RIFF"
                and contents[8:12] == b"WEBP"
            )
        }

        if extension in signatures and not signatures[extension]:
            raise HTTPException(400, "File content does not match its extension.")

       
        filename = f"{uuid4().hex}{extension}"
        saved_path = GREEN_UPLOAD_DIR / filename
        saved_path.write_bytes(contents)

        # Run AI assessment for uploaded images.
        ai_report = None
        ai_status = "NOT_ASSESSED"

        if extension in {".jpg", ".jpeg", ".png", ".webp"}:
            try:
                ai_report = assess_green_evidence(
                    str(saved_path),
                    action_type,
                    description
                )

                status_line = next(
                    (
                        line.strip()
                        for line in ai_report.splitlines()
                        if line.strip().upper() in {
                            "CONSISTENT", "PARTIAL",
                            "MISMATCH", "INSUFFICIENT"
                        }
                    ),
                    None
                )

                ai_status = status_line or "ASSESSMENT_COMPLETE"

            except Exception as error:
                print(f"AI evidence assessment failed: {error}")
                ai_report = "AI assessment unavailable. Please try again."
                ai_status = "ASSESSMENT_FAILED"

        # Prototype scoring: submissions receive 10 points.
        # AI assessment is advisory, not independent verification.

        # Prototype scoring: submitted records receive 10 points.
        # This is not proof that an action has been independently verified.
        save_green_action(
            action_type=action_type,
            description=description,
            evidence_path=str(saved_path).replace("\\", "/"),
            latitude=latitude,
            longitude=longitude,
            points=10
        )

        
        return {
            "message": "Green action saved successfully.",
            "points_earned": 10,
            "ai_status": ai_status,
            "ai_report": ai_report,
            "stats": get_green_stats()
        }

    except HTTPException:
        raise
    except Exception:
        if saved_path and saved_path.exists():
            saved_path.unlink()
        raise HTTPException(500, "Could not save the green action.")
    finally:
        await file.close()


@app.get("/green-stats")
def green_stats():
    return get_green_stats()


@app.get("/green-history")
def green_history():
    return get_green_history()


@app.get("/freshguard")
def freshguard_page():
    return FileResponse("frontend/freshguard.html")


@app.get("/ecorescue")
def ecorescue_page():
    return FileResponse("frontend/ecorescue.html")



@app.post("/freshguard-check")
async def freshguard_check(
    product: str = Form(...),
    purchase_date: str = Form(""),
    expiry_date: str = Form(""),
    storage: str = Form(""),
    file: UploadFile | None = File(None)
):
    product = product.strip()
    if not product or len(product) > 200:
        raise HTTPException(400, "Enter a valid product name.")

    photo_note = ""
    if file:
        if file.content_type not in {
            "image/jpeg", "image/png", "image/webp"
        }:
            raise HTTPException(400, "Use a JPG, PNG, or WEBP photo.")
        photo_note = (
            f"\nA package photo was uploaded: {file.filename}. "
            "Do not claim to have visually inspected it unless image "
            "analysis is actually performed."
        )
        await file.close()

    prompt = f"""
You are FreshGuard AI, a cautious food-safety and food-waste assistant.

Product: {product}
User-entered expiry/best-before date: {expiry_date or "Not provided"}
Storage and opening details: {storage or "Not provided"}
Purchase date: {purchase_date or "Not provided"}
{photo_note}
Explain:
1. What the supplied date can and cannot tell us.
2. Relevant storage guidance and what details are missing.
3. Warning signs and when to discard the food.
4. Ways to avoid food waste if it is suitable to use.

Never guarantee food is safe based only on its name or date.
Distinguish best-before quality dates from safety-related use-by dates
where relevant. Do not invent product-specific facts. If unsure, say so.
"""
    result = ask_ai(prompt)
    return {"result": str(result)}


@app.post("/ecorescue-plan")
async def ecorescue_plan(
    item: str = Form(...),
    condition: str = Form("")
):
    item = item.strip()
    if not item or len(item) > 200:
        raise HTTPException(400, "Enter a valid item name.")

    prompt = f"""
You are EcoRescue AI, a practical circular-economy assistant.

Item: {item}
Condition and known materials: {condition or "Not provided"}

Create a useful action plan:
1. Identify likely materials, noting uncertainty.
2. Suggest safe repair or reuse options.
3. Explain donation or recycling options.
4. Explain what should not go into ordinary recycling.
5. Give a simple step-by-step plan.
6. Describe potential environmental benefits qualitatively.
7. Flag electrical, chemical, sharp-object, or other safety risks.

Do not invent local recycling services or claim exact environmental savings.
Prioritize safe, affordable options.
"""
    result = ask_ai(prompt)
    return {"result": str(result)}