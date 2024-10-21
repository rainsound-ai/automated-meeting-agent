from fastapi import APIRouter, HTTPException
import os
import traceback
import logging
from contextlib import asynccontextmanager
from typing import Dict
# from tenacity import retry, stop_after_attempt, wait_exponential, RetryError

from app.services.summarize import decomposed_summarize_transcription_and_upload_to_notion  
from app.services.llm_conversation_handler import handle_llm_conversation
from app.services.html_docx_or_pdf_handler import handle_html_docx_or_pdf
from app.services.youtube_handler import (
    handle_youtube_videos
)
from app.helpers.youtube_helpers import (
    contains_the_string_youtube,
    title_is_not_a_url
)
from app.services.notion import (
    set_summarized_checkbox_on_notion_page_to_true,
    upload_transcript_to_notion,
    get_unsummarized_links_from_notion,
    block_tracker, 
    rollback_blocks,
    create_toggle_block
)

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

# @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def process_link(item_to_process):
    async with meeting_processing_context(item_to_process):
        try: 
            page_id: str = item_to_process['id']
            is_llm_conversation = False
            link_from_notion = item_to_process['properties']['Link']['title'][0]['plain_text']
            llm_conversation_file_name = None
            is_llm_conversation = False
            

            if contains_the_string_youtube(link_from_notion):
                transcription = await handle_youtube_videos(link_from_notion)
            elif title_is_not_a_url(link_from_notion):
            # 🤮 using title_is_not_a_url to identify if we're looking at an LLM summary smells 
            # but we'll use it for now since we're not sure what all kinds of things we want to handle
               transcription, llm_conversation_file_name = await handle_llm_conversation(item_to_process)
               is_llm_conversation = True 
            else: 
            # Handle pdf, docx, or html
                transcription = await handle_html_docx_or_pdf(link_from_notion)

            # # Create toggle blocks once
            summary_toggle_id = await create_toggle_block(page_id, "Summary", "green")
            transcript_toggle_id = await create_toggle_block(page_id, "Transcript", "orange")
            
            # # Pass the created toggle IDs to the respective functions
            await decomposed_summarize_transcription_and_upload_to_notion(page_id, transcription, summary_toggle_id, is_llm_conversation, llm_conversation_file_name)
            await upload_transcript_to_notion(transcript_toggle_id, transcription)
        except Exception as e:
            logger.error(f"🚨 Error in process_link for meeting {item_to_process['id']}: {str(e)}")
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
            # except RetryError as e:
            #     logger.error(f"🚨 Failed to process meeting {link['id']} after all retry attempts: {str(e)}")
            except Exception as e:
                logger.error(f"🚨 Unexpected error processing meeting {link['id']}: {str(e)}")

        return {"message": "Processing completed"}
    
    except Exception as e:
        logger.error(f"🚨 Error in update_notion_with_transcript_and_summary: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error updating Notion with transcript and summary: {str(e)}")