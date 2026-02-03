import utils.net
import utils.clients
import utils.http_session
import utils.transport
import utils.session
import shutil
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
import os
import uuid
from ai_engine import process_excel

app = FastAPI()

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


app = FastAPI()


@app.post("/analyze")
async def analyze_excel(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())

    input_path = os.path.join(UPLOAD_DIR, f"{file_id}.xlsx")
    output_path = os.path.join(OUTPUT_DIR, f"{file_id}_analyzed.xlsx")

    print("📥 Saving uploaded file to:", input_path)

    # ✅ SAFE way to save UploadFile
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 🔍 VERIFY file exists and size > 0
    if not os.path.exists(input_path):
        raise Exception("Uploaded file was not saved")

    file_size = os.path.getsize(input_path)
    print("📦 Uploaded file size:", file_size)

    if file_size == 0:
        raise Exception("Uploaded file is empty")

    print("🧠 Starting AI processing...")
    process_excel(input_path, output_path)

    if not os.path.exists(output_path):
        raise Exception("Output file not created")

    print("✅ Analysis complete. Sending file:", output_path)

    return FileResponse(
        output_path,
        filename="ai_business_analysis.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
