from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from yt_dlp import YoutubeDL
import os
import uuid
import subprocess
import requests

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
        if "youtube.com" in query or "youtu.be" in query:
            vid = query.split("v=")[-1].split("&")[0] if "v=" in query else query.split("/")[-1]
            info = requests.get(f"https://yewtu.be/api/v1/videos/{vid}")
            if info.status_code != 200:
                return JSONResponse(content={"error": "Failed to fetch metadata"}, status_code=500)
    except Exception as e:
        return JSONResponse(content={"error": "Video metadata fetch failed", "details": str(e)}, status_code=500)

    filename_id = str(uuid.uuid4())
    temp_file = f"{filename_id}_orig.mp3"
    output_file = f"{filename_id}_trim.{format}"
    temp_path = os.path.join(OUTPUT_DIR, temp_file)
    final_path = os.path.join(OUTPUT_DIR, output_file)

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": temp_path,
        "quiet": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([query])
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", temp_path,
            "-ss", str(start), "-to", str(end),
            final_path
        ], check=True)

        os.remove(temp_path)
        return {"file_url": f"/download/{output_file}"}
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
