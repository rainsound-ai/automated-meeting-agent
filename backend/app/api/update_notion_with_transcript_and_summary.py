import logging
from fastapi import APIRouter, HTTPException, UploadFile
import traceback
from io import BytesIO
from contextlib import asynccontextmanager
import os
from typing import Dict
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
from pytubefix import YouTube
from pytubefix.cli import on_progress
import re
import aiofiles
import requests
from bs4 import BeautifulSoup
import PyPDF2
import io
import docx
import re

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

def title_is_not_a_url(link):
    return True

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def process_link(meeting):
    async with meeting_processing_context(meeting):
        try: 
            page_id: str = meeting['id']
            link_from_notion = meeting['properties']['Link']['title'][0]['plain_text']
            if contains_the_string_youtube(link_from_notion):
            # Handle youtube videos
                logger.info("💡 About to download youtube video")
                video_path, captions_available = await download_youtube_video(link_from_notion)
                print("🚨video path", video_path)

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
                
                    async with aiofiles.open(video_path, 'rb') as f:
                        file_content = await f.read()
                    
                    temp_upload_file = UploadFile(
                        filename=os.path.basename(video_path),
                        file=BytesIO(file_content),
                    )
                    transcription = await transcribe(temp_upload_file)

                    try:
                        logger.info("💡 Removing youtube audio file")   
                        os.remove(video_path)
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
                    
                    # Parse the HTML content
                    soup = BeautifulSoup(response.text, 'html.parser')
                    text = soup.get_text(separator='\n', strip=True)
                    cleaned_text = '\n'.join(line.strip() for line in text.split('\n') if line.strip())
                    
                    transcription = cleaned_text 
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
async def download_youtube_video(youtube_url: str) -> str:
    logger.info(f"💡 Downloading video from YouTube link: {youtube_url}")
    captions_available = False
    video_path = None
    
    try:
        yt = YouTube(youtube_url, on_progress_callback = on_progress)
        print("🚨video title", yt.title)
        
        youtube_captions = yt.captions['en']
        if youtube_captions:
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

            captions_available = True
        else:
            logger.info("🚨 No captions available for this video.")
            youtube_audio = yt.streams.get_audio_only()
            video_path = youtube_audio.download(mp3=True)
            captions_available = False
        return video_path, captions_available
 
    
    except Exception as e:
        logger.error(f"🚨 Error downloading YouTube video: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error downloading YouTube video: {str(e)}")