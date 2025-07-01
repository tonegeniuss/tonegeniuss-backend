from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from yt_dlp import YoutubeDL
import os
import uuid
import subprocess

app = FastAPI()

OUTPUT_DIR = "downloads"
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.get("/")
def root():
    return {"status": "ToneGeniuss Backend Running"}

@app.get("/extract-audio/")
def extract_audio(query: str = Query(..., description="YouTube URL or song name"),
                  start: float = Query(0, description="Start time in seconds"),
                  end: float = Query(30, description="End time in seconds"),
                  format: str = Query("mp3", description="mp3 or m4r")):

    filename_id = str(uuid.uuid4())
    temp_file = f"{filename_id}.mp3"
    output_file = f"{filename_id}.{format}"
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

    with YoutubeDL(ydl_opts) as ydl:
        try:
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
        return JSONResponse(content={"error": "FFmpeg trim failed", "details": str(e)}, status_code=500)

@app.get("/download/{filename}")
def download_file(filename: str):
    path = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(path):
        return FileResponse(path, media_type="audio/mpeg", filename=filename)
    return JSONResponse(content={"error": "File not found"}, status_code=404)