
import io
import re
import PyPDF2
import docx
from bs4 import BeautifulSoup
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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