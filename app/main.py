from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import os
import uuid
import subprocess
import requests
from urllib.parse import parse_qs, urlparse

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
def extract_audio(
    query: str = Query(...),
    start: float = Query(0),
    end: float = Query(30),
    format: str = Query("mp3")
):
    # Determine video ID
    vid = None
    if "youtu" in query:
        p = urlparse(query)
        qs = parse_qs(p.query)
        vid = qs.get("v", [None])[0]
    else:
        r = requests.get(f"https://yewtu.be/api/v1/search?q={query}")
        data = r.json()
        if not data:
            return JSONResponse({"error": "No search results"}, status_code=400)
        vid = data[0]["videoId"]

    if not vid:
        return JSONResponse({"error": "Invalid YouTube link or no results"}, status_code=400)

    # Fetch audio stream URL via Invidious
    info = requests.get(f"https://yewtu.be/api/v1/videos/{vid}").json()
    formats = info.get("adaptiveFormats", [])
    audio_fmt = next((f for f in formats if f["mimeType"].startswith("audio")), None)
    if not audio_fmt:
        return JSONResponse({"error": "No audio format found"}, status_code=500)
    source_url = audio_fmt["url"]

    # Download & trim
    filename_id = str(uuid.uuid4())
    temp_path  = os.path.join(OUTPUT_DIR, f"{filename_id}_orig.mp3")
    final_path = os.path.join(OUTPUT_DIR, f"{filename_id}_trim.{format}")

    subprocess.run(
        ["curl", "-L", source_url, "-o", temp_path],
        check=True
    )

    subprocess.run([
        "ffmpeg", "-y",
        "-ss", str(start), "-to", str(end),
        "-i", temp_path,
        final_path
    ], check=True)

    os.remove(temp_path)
    return {"file_url": f"/download/{filename_id}_trim.{format}"}

@app.get("/download/{filename}")
def download_file(filename: str):
    path = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(path):
        return FileResponse(path, media_type="audio/mpeg", filename=filename)
    return JSONResponse({"error": "File not found"}, status_code=404)
