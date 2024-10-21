import logging
from fastapi import APIRouter, HTTPException, UploadFile
import traceback
from io import BytesIO
from contextlib import asynccontextmanager
from app.services.transcribe import transcribe
from app.services.summarize import decomposed_summarize_transcription_and_upload_to_notion  
import os
from typing import List, Dict
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
# from pytubefix import YouTube
# from pytubefix.cli import on_progress
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptAvailable, VideoUnavailable
import re
import aiofiles
import requests
from bs4 import BeautifulSoup
import PyPDF2
import io
import docx
import re
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

def contains_the_string_youtube(link):
    link_lower = link.lower()
    return "youtube" in link_lower or "youtu.be" in link_lower

def get_video_id(url):
    pattern = r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def process_link(meeting):
    async with meeting_processing_context(meeting):
        try: 
            page_id: str = meeting['id']
            link_from_notion = meeting['properties']['Link']['title'][0]['plain_text']
            if contains_the_string_youtube(link_from_notion):
                logger.info("💡 About to download youtube video")
                video_id = get_video_id(link_from_notion)
                captions_available = get_captions(video_id)
                # video_path, captions_available = await download_youtube_video(link_from_notion, "./downloads")
                if captions_available:
                    logger.info("💡 Captions available")
                    with open("captions.txt") as f:
                        transcription = f.read()
                # else:
                #     transcription = await transcribe(video_path)
                
                #     async with aiofiles.open(video_path, 'rb') as f:
                #         file_content = await f.read()
                    
                #     temp_upload_file = UploadFile(
                #         filename=os.path.basename(video_path),
                #         file=BytesIO(file_content),
                #     )
                #     transcription = await transcribe(temp_upload_file)

                try:
                    logger.info("💡 Removing temp files")   
                    os.remove("captions.txt")
                    # os.remove(video_path)
                except Exception as e:
                    logger.error(f"🚨 Error removing temp files: {str(e)}")
                    traceback.print_exc()
            else: 
                transcription = extract_text_from_link(link_from_notion)
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

def extract_text_from_link(url):
    try:
        response = requests.get(url)
        content_type = response.headers.get('Content-Type', '').lower()

        if 'application/pdf' in content_type:
            return extract_text_from_pdf(response.content)
        elif 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' in content_type:
            return extract_text_from_docx(response.content)
        elif 'text/html' in content_type:
            return extract_text_from_html(response.text)
        else:
            return extract_text_from_html(response.text)  # Default to HTML parsing
    except Exception as e:
        logger.error(f"🚨 Error extracting text from {url}: {str(e)}")
        return ""

def extract_text_from_pdf(content):
    pdf_file = io.BytesIO(content)
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"
    return clean_text(text)

def extract_text_from_docx(content):
    docx_file = io.BytesIO(content)
    doc = docx.Document(docx_file)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return clean_text(text)

def extract_text_from_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    for script in soup(["script", "style"]):
        script.decompose()
    text = soup.get_text()
    return clean_text(text)

def clean_text(text):
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters and digits
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    return text.strip()

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
def get_captions(video_id):
    captions_available = False
    transcript = None

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        captions_available = True

        # save the captions to a file called captions.txt
        with open("captions.txt", "w") as f:
            for line in transcript:
                f.write(f"{line['text']}\n")

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
    except NoTranscriptAvailable:
        print(f"No transcript available for video: {video_id}")
    except VideoUnavailable:
        print(f"Video {video_id} is unavailable")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

    return captions_available
