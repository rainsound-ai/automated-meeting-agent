import logging
from fastapi import APIRouter, HTTPException, UploadFile
import traceback
from io import BytesIO
from contextlib import asynccontextmanager
import os
from typing import Dict
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
import re
import aiofiles
import requests
from bs4 import BeautifulSoup

from app.services.transcribe import transcribe
from app.services.summarize import decomposed_summarize_transcription_and_upload_to_notion  
from app.services.notion import (
    set_summarized_checkbox_on_notion_page_to_true,
    upload_transcript_to_notion,
    get_unsummarized_links_from_notion,
    block_tracker, 
    rollback_blocks,
    create_toggle_block
)

from app.helpers.youtube_helpers import (
    contains_the_string_youtube,
    title_is_not_a_url
)

from app.helpers.text_extraction_helpers import extract_text_from_link

from app.services.youtube import get_youtube_captions_or_audio

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
            is_llm_conversation = False
            llm_conversation_file_name = None
            link_from_notion = meeting['properties']['Link']['title'][0]['plain_text']
            if contains_the_string_youtube(link_from_notion):
            # Handle youtube videos
                logger.info("💡 About to download youtube video")
                downloaded_youtube_audio_path, captions_available = await get_youtube_captions_or_audio(link_from_notion)

                if captions_available:
                    # Handle when captions were available
                    with open("captions.txt") as f:
                        transcription = f.read()
                    try:
                        logger.info("💡 Removing captions file")   
                        os.remove("captions.txt")
                    except Exception as e:
                        logger.error(f"🚨 Error removing captions file: {str(e)}")
                        traceback.print_exc()
                else:
                # Handle when we had to transcribe the youtube audio to get a transcript
                    async with aiofiles.open(downloaded_youtube_audio_path, 'rb') as f:
                        file_content = await f.read()
                    
                    temp_upload_file = UploadFile(
                        filename=os.path.basename(downloaded_youtube_audio_path),
                        file=BytesIO(file_content),
                    )
                    transcription = await transcribe(temp_upload_file)

                    try:
                        logger.info("💡 Removing youtube audio file")   
                        os.remove(downloaded_youtube_audio_path)
                    except Exception as e:
                        logger.error(f"🚨 Error removing youtube audio file: {str(e)}")
                        traceback.print_exc()
            elif title_is_not_a_url(link_from_notion):
            # Handle gpt conversation
                llm_conversation = meeting['properties']["LLM Conversation"]["files"][0]
                file_url = llm_conversation['file']['url']
                try:
                    # Download the content from the URL
                    response = requests.get(file_url)
                    response.raise_for_status()  # Raise an exception for bad status codes
                    # get the file name from the response headers
                    llm_conversation_file_name = llm_conversation['name']
                    
                    # Parse the HTML content
                    soup = BeautifulSoup(response.text, 'html.parser')
                    text = soup.get_text(separator='\n', strip=True)
                    cleaned_text = '\n'.join(line.strip() for line in text.split('\n') if line.strip())
                    
                    transcription = cleaned_text 
                    is_llm_conversation = True
                    print("Successfully processed and saved the LLM conversation.")
                except requests.RequestException as e:
                    print(f"Error downloading file: {e}")
                except Exception as e:
                    print(f"Error processing file content: {e}")
            else: 
            # Handle pdf, docx, or html
                transcription = extract_text_from_link(link_from_notion)

            # # Create toggle blocks once
            summary_toggle_id = await create_toggle_block(page_id, "Summary", "green")
            transcript_toggle_id = await create_toggle_block(page_id, "Transcript", "orange")
            
            # # Pass the created toggle IDs to the respective functions
            await decomposed_summarize_transcription_and_upload_to_notion(page_id, transcription, summary_toggle_id, is_llm_conversation, llm_conversation_file_name)
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