import requests
import logging

from app.helpers.text_extraction_helpers import (
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_text_from_html
)
from app.services.punctuation_agent import punctuate_transcript

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
async def handle_html_docx_or_pdf(url):
    transcript = ""
    punctuated_transcript = ""
    try:
        response = requests.get(url)
        content_type = response.headers.get('Content-Type', '').lower()

        if 'application/pdf' in content_type:
            transcript = extract_text_from_pdf(response.content)
        elif 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' in content_type:
            transcript = extract_text_from_docx(response.content)
        elif 'text/html' in content_type:
            transcript = extract_text_from_html(response.text)
        else:
            transcript = extract_text_from_html(response.text)  # Default to HTML parsing
        punctuated_transcript = punctuate_transcript(transcript)
        return punctuated_transcript, "link_database"
    except Exception as e:
        logger.error(f"🚨 Error extracting text from {url}: {str(e)}")
        return ""