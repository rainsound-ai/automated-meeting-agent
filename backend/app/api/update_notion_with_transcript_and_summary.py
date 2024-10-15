import logging
from fastapi import APIRouter, HTTPException, UploadFile
import traceback
from io import BytesIO
from contextlib import asynccontextmanager
from app.services.transcribe import transcribe
from app.services.summarize import decomposed_summarize_transcription_and_upload_to_notion  
import os
import httpx
import asyncio
from app.services.notion import (
    set_summarized_checkbox_on_notion_page_to_true,
    upload_transcript_to_notion,
    get_unsummarized_links_from_notion,
    block_tracker, 
    rollback_blocks,
    create_toggle_block
)
from typing import List, Dict
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
from pytubefix import YouTube
from pytubefix.cli import on_progress
import re
import aiofiles

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
api_router = APIRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def meeting_processing_context(meeting):
    block_tracker.clear()
    try:
        yield
    except Exception as e:
        logger.error(f"🚨 Error processing meeting {meeting['id']}: {str(e)}")
        await rollback_blocks()
        raise
    else:
        await set_summarized_checkbox_on_notion_page_to_true(meeting['id'])


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def process_link(meeting):
    async with meeting_processing_context(meeting):
        try: 
            page_id: str = meeting['id']
            link_from_notion = meeting['properties']['Link']['title'][0]['plain_text']
            print("link from notion 🚨", link_from_notion)
            video_path, captions_available = await download_youtube_video(link_from_notion, "./downloads")

            if captions_available:
                with open("captions.txt") as f:
                    transcription = f.read()
            else:
                transcription = await transcribe(video_path)
            
                async with aiofiles.open(video_path, 'rb') as f:
                    file_content = await f.read()
                
                temp_upload_file = UploadFile(
                    filename=os.path.basename(video_path),
                    file=BytesIO(file_content),
                )
                transcription = await transcribe(temp_upload_file)
                print(transcription)
            
            # # Create toggle blocks once
            summary_toggle_id = await create_toggle_block(page_id, "Summary", "green")
            transcript_toggle_id = await create_toggle_block(page_id, "Transcript", "orange")
            
            # # Pass the created toggle IDs to the respective functions
            await decomposed_summarize_transcription_and_upload_to_notion(transcription, summary_toggle_id)
            await upload_transcript_to_notion(transcript_toggle_id, transcription)
        except Exception as e:
            logger.error(f"🚨 Error in process_link for meeting {meeting['id']}: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise

@api_router.post("/update_notion_with_transcript_and_summary")
async def update_notion_with_transcript_and_summary() -> Dict[str, str]:
    logger.info("Received request for updating Notion with transcript and summary.")
    try:
        links_to_summarize = await get_unsummarized_links_from_notion()
        logger.info(f"💡 Found {len(links_to_summarize)} links to summarize.")

        for link in links_to_summarize:
            try:
                await process_link(link)
                logger.info(f"✅ Successfully processed meeting {link['id']}")
            except RetryError as e:
                logger.error(f"🚨 Failed to process meeting {link['id']} after all retry attempts: {str(e)}")
            except Exception as e:
                logger.error(f"🚨 Unexpected error processing meeting {link['id']}: {str(e)}")

        return {"message": "Processing completed"}
    
    except Exception as e:
        logger.error(f"🚨 Error in update_notion_with_transcript_and_summary: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error updating Notion with transcript and summary: {str(e)}")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def download_youtube_video(youtube_url: str, output_path: str = "./") -> str:
    logger.info(f"💡 Downloading video from YouTube link: {youtube_url}")
    
    try:
        yt = YouTube(youtube_url, on_progress_callback = on_progress)
        print("🚨video title", yt.title)
        youtube_audio = yt.streams.get_audio_only()
        video_path = youtube_audio.download(mp3=True)

        captions_available = False
        youtube_captions = yt.captions['en']
        
        if youtube_captions:
            captions_available = True
            # Remove caption numbers and timestamps
            youtube_captions.save_captions("captions.txt")
            
            # get the file called captions.txt at the root of the directory
            with open("captions.txt") as f:
                youtube_captions_txt = f.read()

            cleaned_captions = re.sub(r'^\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}\n', '', youtube_captions_txt, flags=re.MULTILINE)

            # Remove any remaining empty lines
            cleaned_captions = re.sub(r'\n\s*\n', '\n', cleaned_captions)

            # Remove leading/trailing whitespace from each line
            cleaned_captions = '\n'.join(line.strip() for line in cleaned_captions.split('\n') if line.strip())

            # save cleaned captions to a file called captions.txt
            with open("captions.txt", "w") as f:
                f.write(cleaned_captions)
        return video_path, captions_available
 
    
    except Exception as e:
        logger.error(f"🚨 Error downloading YouTube video: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error downloading YouTube video: {str(e)}")