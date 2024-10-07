# main.py
import os
import tempfile
import uuid
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import openai
import deepl
from pydub import AudioSegment
import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Read API keys from environment variables
openai.api_key = os.getenv("OPENAI_API_KEY")
deepl_api_key = os.getenv("DEEPL_API_KEY")

if not openai.api_key or not deepl_api_key:
    raise ValueError("Please set the OPENAI_API_KEY and DEEPL_API_KEY environment variables.")

# Initialize DeepL translator
translator = deepl.Translator(deepl_api_key)

# Whisper language codes
whisper_languages = {
    "English": "en",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Italian": "it",
    "Portuguese": "pt",
    "Dutch": "nl",
    "Russian": "ru",
    "Chinese": "zh",
    "Japanese": "ja",
    "Korean": "ko"
}

# DeepL language codes
deepl_languages = {
    "English": "EN-US",
    "Spanish": "ES",
    "French": "FR",
    "German": "DE",
    "Italian": "IT",
    "Portuguese": "PT-PT",
    "Dutch": "NL",
    "Russian": "RU",
    "Chinese": "ZH",
    "Japanese": "JA"
}

def extract_audio(video_path, output_path, compress=True, quality=5):
    print(f"Starting audio extraction from {video_path}")
    file_extension = os.path.splitext(video_path)[1].lower()
    
    try:
        if file_extension in ['.mp4', '.mov']:
            print(f"Detected {file_extension} file, using pydub to extract audio")
            audio = AudioSegment.from_file(video_path, format=file_extension[1:])  # Remove the dot from extension
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
        
        print(f"Exporting audio to {output_path}")
        if compress:
            audio.export(output_path, format="ogg", parameters=["-q:a", str(quality)])
        else:
            audio.export(output_path, format="wav")
        print("Audio extraction completed")
    except Exception as e:
        print(f"Error during audio extraction: {str(e)}")
        raise

def transcribe_audio(audio_path, language):
    print(f"Starting audio transcription for {audio_path}")
    with open(audio_path, "rb") as audio_file:
        transcript = openai.Audio.transcribe("whisper-1", audio_file, language=language, response_format="verbose_json")
    print("Transcription completed")
    return transcript

def create_srt(transcript, output_path):
    print(f"Creating SRT file at {output_path}")
    with open(output_path, "w", encoding="utf-8") as srt_file:
        for i, segment in enumerate(transcript['segments'], 1):
            start_time = format_timestamp(int(segment['start'] * 1000))
            end_time = format_timestamp(int(segment['end'] * 1000))
            text = segment['text'].strip()
            srt_file.write(f"{i}\n{start_time} --> {end_time}\n{text}\n\n")
    print("SRT file created")

def format_timestamp(ms):
    """Convert milliseconds to SRT timestamp format"""
    seconds, ms = divmod(ms, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"

def translate_srt(input_path, target_lang):
    print(f"Starting translation of {input_path} to {target_lang}")
    with open(input_path, "r", encoding="utf-8") as input_file:
        content = input_file.read()
    
    translated_content = translator.translate_text(content, target_lang=target_lang)
    print("Translation completed")
    return str(translated_content)

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("static/index.html", "r") as f:
        return f.read()

@app.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    transcription_lang: str = Form(...),
    translation_lang: str = Form(...)
):
    print(f"Received upload request for file: {file.filename}")
    print(f"Transcription language: {transcription_lang}")
    print(f"Translation language: {translation_lang}")
    
    # Generate a unique ID for this job
    job_id = str(uuid.uuid4())
    print(f"Generated job ID: {job_id}")
    
    # Create a directory for this job
    os.makedirs(f"temp/{job_id}", exist_ok=True)
    
    # Save uploaded file
    video_path = f"temp/{job_id}/video{os.path.splitext(file.filename)[1]}"
    with open(video_path, "wb") as buffer:
        buffer.write(await file.read())
    print(f"Saved video file to {video_path}")

    # Extract audio
    audio_path = f"temp/{job_id}/audio.wav"
    extract_audio(video_path, audio_path)
    print(f"Audio extracted to {audio_path}")

    # Transcribe audio
    transcript = transcribe_audio(audio_path, whisper_languages[transcription_lang])

    # Create SRT file
    srt_path = f"temp/{job_id}/transcript.srt"
    create_srt(transcript, srt_path)

    # Translate SRT file
    translated_content = translate_srt(srt_path, deepl_languages[translation_lang])
    translated_srt_path = f"temp/{job_id}/translated_transcript.srt"
    with open(translated_srt_path, "w", encoding="utf-8") as f:
        f.write(translated_content)
    print(f"Saved translated transcript to {translated_srt_path}")

    print(f"Processing completed for job {job_id}")
    return {"job_id": job_id}

@app.get("/result/{job_id}")
async def get_result(job_id: str):
    print(f"Fetching results for job {job_id}")
    srt_path = f"temp/{job_id}/transcript.srt"
    translated_srt_path = f"temp/{job_id}/translated_transcript.srt"
    
    with open(srt_path, "r", encoding="utf-8") as f:
        original_transcript = f.read()
    
    with open(translated_srt_path, "r", encoding="utf-8") as f:
        translated_transcript = f.read()
    
    print(f"Returning results for job {job_id}")
    return {
        "original_transcript": original_transcript,
        "translated_transcript": translated_transcript
    }

@app.get("/download/{job_id}/{file_type}")
async def download_file(job_id: str, file_type: str):
    print(f"Download request for job {job_id}, file type: {file_type}")
    if file_type == "original":
        file_path = f"temp/{job_id}/transcript.srt"
        filename = "transcript.srt"
    elif file_type == "translated":
        file_path = f"temp/{job_id}/translated_transcript.srt"
        filename = "translated_transcript.srt"
    else:
        print(f"Invalid file type requested: {file_type}")
        return {"error": "Invalid file type"}
    
    print(f"Serving file: {file_path}")
    return FileResponse(file_path, filename=filename)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
