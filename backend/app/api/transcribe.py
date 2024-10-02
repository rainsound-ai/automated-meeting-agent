from app.lib.Env import open_ai_api_key
from app.models import TranscriptionResponse
from fastapi import APIRouter, File, UploadFile, HTTPException
import os
import uuid
import shutil
import subprocess
from openai import OpenAI
import gc

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))

client = OpenAI(api_key=open_ai_api_key)

api_router = APIRouter()

# Function to clear the temp directory
def clear_temp_directory():
    temp_dir = 'temp'
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)
    print("Temp directory cleared.")

# Function to chunk audio file using ffmpeg
def chunk_audio(input_file, output_dir, chunk_size_bytes=26214400):
    print(f"Chunking audio file: {input_file}")

    chunk_duration_sec = chunk_size_bytes // (64 * 1024)  # Approximate chunk duration based on bitrate (64k)
    output_pattern = os.path.join(output_dir, "chunk_%03d.mp3")
    
    # Use ffmpeg to split the audio into chunks
    command = [
        'ffmpeg', '-i', input_file, '-f', 'segment', '-segment_time', str(chunk_duration_sec),
        '-c', 'copy', output_pattern
    ]
    
    subprocess.run(command, check=True)
    print(f"Audio file chunked and saved to {output_dir}")

# Function to transcribe a chunk
def transcribe_then_delete_chunk(chunk_path, idx):
    print(f"Transcribing chunk {idx} from {chunk_path}")

    if not os.path.exists(chunk_path):
        raise FileNotFoundError(f"Chunk file {chunk_path} does not exist.")

    with open(chunk_path, "rb") as chunk_file:
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=chunk_file,
            response_format="text"
        )
        print(f"Chunk {idx} transcribed successfully.")
    
    os.remove(chunk_path)
    print(f"Chunk {idx} deleted after transcription.")
    return idx, result

# Main API route
@api_router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe(file: UploadFile = File(...)):
    clear_temp_directory()

    if not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an audio file.")

    try:
        file_extension = os.path.splitext(file.filename)[1]
        temp_filename = f"{uuid.uuid4()}{file_extension}"
        temp_path = os.path.join("temp", temp_filename)
        temp_dir = 'temp'

        # Save the uploaded file
        with open(temp_path, "wb") as buffer:
            while content := await file.read(1024 * 1024):  # Read in 1MB chunks
                buffer.write(content)
        print(f"File {file.filename} saved to {temp_path}.")

        # Chunk the audio using ffmpeg
        chunk_audio(temp_path, temp_dir)

        # Process each chunk sequentially
        final_transcription = ""
        chunk_files = sorted([f for f in os.listdir(temp_dir) if f.startswith("chunk_")])

        for idx, chunk_file in enumerate(chunk_files):
            chunk_path = os.path.join(temp_dir, chunk_file)

            # Transcribe chunk
            idx, transcription = transcribe_then_delete_chunk(chunk_path, idx)
            final_transcription += transcription + " "  # Append transcription

            # Free up memory
            gc.collect()

        # Clean up the original file
        os.remove(temp_path)
        print("Temporary files cleaned up.")

        # Save final transcription to a file
        transcription_file_path = os.path.join(BASE_DIR, 'transcription.txt')
        with open(transcription_file_path, 'w') as file_handle:
            file_handle.write(f"File Name: {file.filename}\n\n{final_transcription.strip()}")
        print(f"Transcription saved to {transcription_file_path}.")

        return {"transcription": final_transcription.strip()}

    except Exception as e:
        clear_temp_directory()
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
