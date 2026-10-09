const fileInput = document.getElementById("fileInput");
const uploadButton = document.getElementById("uploadButton");
const uploadStatus = document.getElementById("uploadStatus");

const promptInput = document.getElementById("prompt");
const askButton = document.getElementById("askButton");

const responseBox = document.getElementById("response");
const loading = document.getElementById("loading");
const errorBox = document.getElementById("error");

function showError(message) {
errorBox.textContent = "Error: " + message;
errorBox.hidden = false;
}

function showResult(result) {
if (typeof result === "object" && result !== null) {
responseBox.textContent =
result.answer || JSON.stringify(result, null, 2);
} else {
responseBox.textContent = String(result ?? "");
}
}

// ASK AI
askButton.addEventListener("click", async () => {
const prompt = promptInput.value.trim();


errorBox.hidden = true;

if (!prompt) {
    showError("Please enter a question first.");
    return;
}

askButton.disabled = true;
loading.hidden = false;
responseBox.textContent = "";

try {
    const response = await fetch("/ask", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ prompt })
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.detail || "AI request failed.");
    }

    showResult(data.result);
} catch (error) {
    console.error("Ask AI error:", error);
    showError(error.message);
} finally {
    loading.hidden = true;
    askButton.disabled = false;
}


});

// FILE UPLOAD
uploadButton.addEventListener("click", async () => {
const file = fileInput.files[0];


errorBox.hidden = true;

if (!file) {
    uploadStatus.textContent = "Please select a file first.";
    return;
}

const isImage = file.type.startsWith("image/");
const isPDF = file.type === "application/pdf";

if (!isImage && !isPDF) {
    showError("Please select an image or PDF file.");
    return;
}

uploadButton.disabled = true;
loading.hidden = false;
responseBox.textContent = "";
uploadStatus.textContent = "Processing file...";

try {
    const formData = new FormData();
    formData.append("file", file);

    let url = "/upload";

    if (isImage) {
        const instruction = `


You are RE:VIVE, an e-waste recovery assistant. Analyze the uploaded image and create a concise Recovery Passport.

IDENTIFIED ITEM: Identify the object.
MATERIALS: List likely materials and distinguish guesses from visible evidence. Do not claim exact metal quantities.
HAZARDS: Identify visible risks. Recommend safe handling; never advise dismantling, burning, or puncturing batteries.
RECOVERY: Explain what professional recyclers may recover. Do not invent quantities, prices, or CO2 savings.
ACTION: Recommend safe reuse, repair, donation, or authorized e-waste collection.
ENVIRONMENT: Explain potential benefits of responsible recycling.
CONFIDENCE: Give high, medium, or low confidence and explain uncertainty.

Use clear headings and brief bullets. If the image is not e-waste, identify what is actually shown. Check local recycling guidance. This is not a certified safety inspection.
`;

        url = "/analyze-image?instruction=" +
            encodeURIComponent(instruction);
    }

    const response = await fetch(url, {
        method: "POST",
        body: formData
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.detail || "File processing failed.");
    }

    if (isImage) {
        showResult(data.result);
    } else {
        showResult(
            data.analysis ||
            data.extracted_text ||
            "The PDF was uploaded, but no text or analysis was returned."
        );
    }

    uploadStatus.textContent = "Processed: " + data.filename;
} catch (error) {
    console.error("Upload error:", error);
    showError(error.message);
    uploadStatus.textContent = "Processing failed.";
} finally {
    loading.hidden = true;
    uploadButton.disabled = false;
}


});
