import logging
from fastapi import APIRouter, HTTPException, UploadFile
import traceback
import requests
from io import BytesIO
from contextlib import asynccontextmanager
from app.services.transcribe import transcribe
from app.services.summarize import decomposed_summarize_transcription_and_upload_to_notion  
import os
from app.services.notion import (
    set_summarized_checkbox_on_notion_page_to_true,
    upload_transcript_to_notion,
    get_meetings_with_jumpshare_links_and_unsummarized_from_notion,
    block_tracker, 
    rollback_blocks,
    create_toggle_block
)
from typing import List, Dict
from app.models import (
    Meeting,
    Transcription,
    JumpshareLink
)
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
api_router = APIRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def meeting_processing_context(meeting: Meeting):
    block_tracker.clear()
    try:
        yield
    except Exception as e:
        logger.error(f"Error processing meeting {meeting['id']}: {str(e)}")
        await rollback_blocks()
        raise
    else:
        await set_summarized_checkbox_on_notion_page_to_true(meeting['id'])

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def process_meeting(meeting: Meeting):
    async with meeting_processing_context(meeting):
        page_id: str = meeting['id']
        jumpshare_video = await get_video_from_jumpshare_link(JumpshareLink(url=meeting['properties']['Jumpshare Link']['url']))
        transcription: Transcription = await transcribe(jumpshare_video)
        
        # Create toggle blocks once
        summary_toggle_id = await create_toggle_block(page_id, "Summary", "green")
        transcript_toggle_id = await create_toggle_block(page_id, "Transcript", "orange")
        
        # Pass the created toggle IDs to the respective functions
        await decomposed_summarize_transcription_and_upload_to_notion(transcription, summary_toggle_id)
        await upload_transcript_to_notion(transcript_toggle_id, transcription)

@api_router.post("/update_notion_with_transcript_and_summary")
async def update_notion_with_transcript_and_summary() -> Dict[str, str]:
    logger.info("Received request for updating Notion with transcript and summary.")
    try:
        meetings_to_summarize: List[Meeting] = await get_meetings_with_jumpshare_links_and_unsummarized_from_notion()
        logger.info(f"Found {len(meetings_to_summarize)} meetings to summarize.")

        for meeting in meetings_to_summarize:
            try:
                await process_meeting(meeting)
                logger.info(f"Successfully processed meeting {meeting['id']}")
            except RetryError as e:
                logger.error(f"Failed to process meeting {meeting['id']} after all retry attempts: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error processing meeting {meeting['id']}: {str(e)}")

        return {"message": "Processing completed"}
    
    except Exception as e:
        logger.error(f"Error in update_notion_with_transcript_and_summary: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error updating Notion with transcript and summary: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error in update_notion_with_transcript_and_summary: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error updating Notion with transcript and summary: {str(e)}")

import httpx

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def get_video_from_jumpshare_link(jumpshare_link: JumpshareLink) -> UploadFile:
    logger.info(f"Getting file from Jumpshare link: {jumpshare_link.url}")
    try:
        modified_link = jumpshare_link.url + "+"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0"
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(modified_link, headers=headers, follow_redirects=True)
            final_url = response.url
            video_response = await client.get(final_url, headers=headers)

            if video_response.status_code == 200:
                video_content = BytesIO(video_response.content)
                video_content.seek(0)
                jumpshare_video = UploadFile(file=video_content, filename="video.mp4")
                return jumpshare_video
            else:
                logger.error(f"Failed to download video. Status code: {video_response.status_code}")
                raise HTTPException(status_code=video_response.status_code, detail="Failed to download video")
    except Exception as e:
        logger.error(f"Error processing Jumpshare link: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Error processing Jumpshare link.")
