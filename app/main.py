from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import requests
import os
import uuid
import subprocess

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR = "downloads"
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.get("/")
def root():
    return {"status": "ToneGeniuss Backend Running"}

@app.get("/extract-audio/")
def extract_audio(query: str = Query(...),
                  start: float = Query(0),
                  end: float = Query(30),
                  format: str = Query("mp3")):

    try:
        vid = query.split("v=")[1].split("&")[0]
        invidious_url = f"https://yewtu.be/api/v1/videos/{vid}"
        response = requests.get(invidious_url)
        info = response.json()
        audio_url = next(f["url"] for f in info["adaptiveFormats"] if "audio" in f["mimeType"])
    except Exception as e:
        return JSONResponse(
            content={"error": "Failed to fetch Invidious audio URL", "details": str(e)},
            status_code=500
        )

    filename_id = str(uuid.uuid4())
    input_path = os.path.join(OUTPUT_DIR, f"{filename_id}_input.{format}")
    output_path = os.path.join(OUTPUT_DIR, f"{filename_id}_trim.{format}")

    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", audio_url,
            "-ss", str(start), "-to", str(end),
            "-c:a", "libmp3lame", output_path
        ], check=True)
        return {"file_url": f"/download/{os.path.basename(output_path)}"}
    except Exception as e:
        return JSONResponse(
            content={"error": "FFmpeg trim failed", "details": str(e)},
            status_code=500
        )

@app.get("/download/{filename}")
def download_file(filename: str):
    path = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(path):
        return FileResponse(path, media_type="audio/mpeg", filename=filename)
    return JSONResponse(content={"error": "File not found"}, status_code=404)
