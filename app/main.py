from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from yt_dlp import YoutubeDL
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

    filename_id = str(uuid.uuid4())
    # Download original mp3
    temp_file   = f"{filename_id}_orig.mp3"
    # Trimmed output file
    output_file = f"{filename_id}_trim.{format}"
    temp_path   = os.path.join(OUTPUT_DIR, temp_file)
    final_path  = os.path.join(OUTPUT_DIR, output_file)

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": temp_path,
        "quiet": True,
        "cookiefile": "cookies.txt",  # your YouTube auth cookies
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }

    # Step 1: Download audio
    with YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([query])
        except Exception as e:
            return JSONResponse(content={"error": str(e)}, status_code=500)

    # Step 2: Trim using ffmpeg
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", temp_path,
            "-ss", str(start), "-to", str(end),
            final_path
        ], check=True)

        # Cleanup original file
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
