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
from app.helpers.youtube_helpers import contains_the_string_youtube
from app.helpers.llm_conversation_helper import link_is_none_and_therefore_this_must_be_an_llm_conversation_html_file
from app.helpers.jumpshare_helper import link_is_jumpshare_link
from app.services.notion import (
    set_summarized_checkbox_on_notion_page_to_true,
    upload_transcript_to_notion,
    get_unsummarized_links_from_notion,
    get_unsummarized_meetings_from_notion,
    block_tracker, 
    rollback_blocks,
    create_toggle_block
)
from app.services.jumpshare_handler import handle_jumpshare_videos

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
            properties = item_to_process.get('properties', {})

            # Defaults 
            is_llm_conversation = False
            link_or_meeting_database = None
            llm_conversation_file_name = None
            is_jumpshare_link = False

            # Build the link to summarize depending on media type
            if properties.get('Link', {}).get('url'):
                # Case: Single link exists
                print("🚨 Found a link from the link summary database")
                links_from_notion = properties.get('Link', {}).get('url')
                link_or_meeting_database = 'link_database'
            elif properties.get('LLM Conversation', {}).get('files'):
                # Case: LLM conversation exists
                print("🚨 Found an LLM conversation")
                links_from_notion = properties.get('LLM Conversation', {}).get('files', [])[0].get('file', '').get("url", "")
                print("🚨links from notion", links_from_notion)
                link_or_meeting_database = 'link_database'
                is_llm_conversation = True
            elif properties.get('Jumpshare Links', {}).get('files'):
                # Case: One or more Jumpshare links exist
                print("🚨 Found a link or links from the meeting summary database")
                links_from_notion = [f.get('name', '') for f in properties.get('Jumpshare Links', {}).get('files', [])]
                link_or_meeting_database = 'meeting_database'
                is_jumpshare_link = True


            # Handle the different types of links
            if not is_llm_conversation and not is_jumpshare_link and contains_the_string_youtube(links_from_notion):  
            # handle youtube
                transcription = await handle_youtube_videos(links_from_notion)
            elif is_llm_conversation:
             # handle llm conversation  
               print("🚨 Found an LLM conversation")
               transcription, llm_conversation_file_name = await handle_llm_conversation(item_to_process)
            elif link_is_jumpshare_link(links_from_notion[0]):
            # Handle jumpshare link
                print("🚨 Found a Jumpshare link")
                transcription = await handle_jumpshare_videos(links_from_notion)
            elif link_or_meeting_database == 'link_database' and not is_llm_conversation: 
            # Handle pdf, docx, or html
                transcription = await handle_html_docx_or_pdf(links_from_notion)

            # # Create toggle blocks once
            summary_toggle_id = await create_toggle_block(page_id, "Summary", "green")
            transcript_toggle_id = await create_toggle_block(page_id, "Transcript", "orange")

            # # Pass the created toggle IDs to the respective functions
            await decomposed_summarize_transcription_and_upload_to_notion(
                page_id, 
                transcription, 
                summary_toggle_id, 
                link_or_meeting_database, 
                is_llm_conversation, 
                is_jumpshare_link, 
                llm_conversation_file_name
            )
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
        meetings_to_summarize = await get_unsummarized_meetings_from_notion()
        items_to_summarize = links_to_summarize + meetings_to_summarize
        logger.info(f"💡 Found {len(items_to_summarize)} links to summarize.")

        for item in items_to_summarize:
            try:
                await process_link(item)
                logger.info(f"✅ Successfully processed meeting {item['id']}")
            # except RetryError as e:
            #     logger.error(f"🚨 Failed to process meeting {link['id']} after all retry attempts: {str(e)}")
            except Exception as e:
                logger.error(f"🚨 Unexpected error processing meeting {item['id']}: {str(e)}")

        return {"message": "Processing completed"}
    
    except Exception as e:
        logger.error(f"🚨 Error in update_notion_with_transcript_and_summary: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error updating Notion with transcript and summary: {str(e)}")