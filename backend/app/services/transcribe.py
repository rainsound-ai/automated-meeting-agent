from app.lib.Env import open_ai_api_key
from fastapi import File, UploadFile, HTTPException
import os
import uuid
from openai import OpenAI
import asyncio
import aiofiles
import tempfile
import logging
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
client = OpenAI(api_key=open_ai_api_key)

async def extract_audio_stream(video_path: str) -> AsyncGenerator[bytes, None]:
    command = [
        'ffmpeg', '-i', video_path, '-vn', '-acodec', 'libmp3lame', '-b:a', '64k',
        '-f', 'mp3', 'pipe:1'
    ]
    process = await asyncio.create_subprocess_exec(
        *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    
    while True:
        chunk = await process.stdout.read(1024 * 1024)  # Read 1MB at a time
        if not chunk:
            break
        yield chunk
    
    await process.wait()
    if process.returncode != 0:
        stderr = await process.stderr.read()
        logger.error(f"🚨 Error extracting audio: {stderr.decode()}")
        raise RuntimeError("Failed to extract audio from video")

async def transcribe_stream(audio_stream: AsyncGenerator[bytes, None]) -> AsyncGenerator[str, None]:
    buffer = b""
    chunk_size = 10 * 1024 * 1024  # 10MB chunks
    
    async for chunk in audio_stream:
        buffer += chunk
        while len(buffer) >= chunk_size:
            chunk_to_transcribe, buffer = buffer[:chunk_size], buffer[chunk_size:]
            transcription = await asyncio.to_thread(
                client.audio.transcriptions.create,
                model="whisper-1",
                file=("chunk.mp3", chunk_to_transcribe, "audio/mpeg"),
                response_format="text"
            )
            yield transcription.strip()
    
    if buffer:
        transcription = await asyncio.to_thread(
            client.audio.transcriptions.create,
            model="whisper-1",
            file=("chunk.mp3", buffer, "audio/mpeg"),
            response_format="text"
        )
        yield transcription.strip()

async def transcribe(file: UploadFile = File(...)) -> str:
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            temp_path = temp_file.name
            async with aiofiles.open(temp_path, "wb") as buffer:
                while content := await file.read(1024 * 1024):  # Read in 1MB chunks
                    await buffer.write(content)
            logger.info(f"💡 File {file.filename} saved to {temp_path}.")

        audio_stream = extract_audio_stream(temp_path)
        transcription_stream = transcribe_stream(audio_stream)
        
        full_transcription = []
        async for transcription_part in transcription_stream:
            full_transcription.append(transcription_part)
        
        return " ".join(full_transcription)

    except Exception as e:
        logger.error(f"🚨 Error in transcription process: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'temp_path' in locals():
            os.unlink(temp_path)
            logger.info("Temporary file cleaned up.")