from app.lib.Env import open_ai_api_key
from fastapi import File, UploadFile, HTTPException
import os
import uuid
from openai import OpenAI
import asyncio
import aiofiles
import tempfile
import logging

logger = logging.getLogger(__name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
client = OpenAI(api_key=open_ai_api_key)

async def extract_audio_from_video(video_path, audio_output_path):
    command = [
        'ffmpeg', '-i', video_path, '-vn', '-acodec', 'libmp3lame', '-b:a', '64k', audio_output_path
    ]
    process = await asyncio.create_subprocess_exec(
        *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    await process.communicate()
    print(f"Audio extracted from video and saved to {audio_output_path}")

async def chunk_audio(input_file, output_dir, chunk_duration_sec=30):
    output_pattern = os.path.join(output_dir, "chunk_%03d.mp3")
    command = [
        'ffmpeg', '-i', input_file, '-f', 'segment', '-segment_time', str(chunk_duration_sec),
        '-c:a', 'libmp3lame', '-b:a', '64k', output_pattern
    ]
    process = await asyncio.create_subprocess_exec(
        *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    await process.communicate()
    print(f"Audio file chunked and saved to {output_dir}")

async def validate_mp3(file_path):
    async with aiofiles.open(file_path, "rb") as file:
        header = await file.read(3)
    if header != b'ID3' and header[:2] != b'\xff\xfb':
        raise ValueError(f"Invalid MP3 file: {file_path}")

async def transcribe_chunk(chunk_path):
    try:
        await validate_mp3(chunk_path)
        
        async with aiofiles.open(chunk_path, "rb") as chunk_file:
            content = await chunk_file.read()
        
        file_size = len(content)
        logger.debug(f"Chunk size: {file_size} bytes")
        
        if file_size > 25 * 1024 * 1024:  # 25 MB limit
            raise ValueError(f"File size ({file_size} bytes) exceeds 25 MB limit")

        result = await asyncio.to_thread(
            client.audio.transcriptions.create,
            model="whisper-1",
            file=("chunk.mp3", content, "audio/mpeg"),
            response_format="text"
        )
        logger.info(f"Successfully transcribed chunk: {chunk_path}")
        print(f"Successfully transcribed chunk: {chunk_path}")
        return result
    except Exception as e:
        logger.error(f"Error transcribing chunk {chunk_path}: {str(e)}")
        raise
    finally:
        os.remove(chunk_path)

async def transcribe(file: UploadFile = File(...)):
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            file_extension = os.path.splitext(file.filename)[1]
            temp_filename = f"{uuid.uuid4()}{file_extension}"
            temp_path = os.path.join(temp_dir, temp_filename)

            # Save the uploaded file
            async with aiofiles.open(temp_path, "wb") as buffer:
                while content := await file.read(1024 * 1024):  # Read in 1MB chunks
                    await buffer.write(content)
            print(f"File {file.filename} saved to {temp_path}.")

            audio_output_path = os.path.join(temp_dir, f"audio_{uuid.uuid4()}.mp3")
            await extract_audio_from_video(temp_path, audio_output_path)
            os.remove(temp_path)  # Remove the original video file
            temp_path = audio_output_path  # Replace with the extracted audio file

            # Chunk the audio using ffmpeg
            await chunk_audio(temp_path, temp_dir)

            # Process chunks concurrently
            chunk_files = sorted([f for f in os.listdir(temp_dir) if f.startswith("chunk_")])
            transcription_tasks = [transcribe_chunk(os.path.join(temp_dir, chunk_file)) for chunk_file in chunk_files]
            transcriptions = await asyncio.gather(*transcription_tasks)

            final_transcription = " ".join(transcriptions)

            # Clean up the original file
            os.remove(temp_path)
            print("Temporary files cleaned up.")

            return final_transcription.strip()

    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))