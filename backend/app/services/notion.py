from typing import List, Dict, Tuple
import requests
from fastapi import HTTPException
from app.lib.Env import notion_api_key, rainsound_meetings_database_id
import traceback
import logging
from app.services.chunk_text import chunk_text
from app.services.parse_markdown_to_notion_blocks import (
    convert_content_to_blocks, 
    parse_rich_text
)
from app.models import (
    NotionBlock, 
    ToggleBlock
)
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError

# Configuration Constants
NOTION_VERSION = "2022-06-28"
NOTION_API_BASE_URL = "https://api.notion.com/v1"
HEADERS = {
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json"
}

logger = logging.getLogger(__name__)

class NotionBlockTracker:
    def __init__(self):
        self.added_blocks = []

    def add_block(self, block_id: str):
        self.added_blocks.append(block_id)

    def clear(self):
        self.added_blocks.clear()

    def get_blocks(self):
        return self.added_blocks

block_tracker = NotionBlockTracker()

def get_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {notion_api_key}",
        **HEADERS
    }

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def append_blocks_to_notion(toggle_id: str, blocks: List[NotionBlock]) -> Dict:
    blocks_url = f"{NOTION_API_BASE_URL}/blocks/{toggle_id}/children"
    headers = get_headers()
    data = {"children": blocks}
    response = requests.patch(blocks_url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()

def rollback_blocks():
    for block_id in block_tracker.get_blocks():
        delete_block(block_id)
    block_tracker.clear()

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def delete_block(block_id: str):
    url = f"{NOTION_API_BASE_URL}/blocks/{block_id}"
    headers = get_headers()
    response = requests.delete(url, headers=headers)
    if response.status_code != 200:
        logger.error(f"Failed to delete block {block_id}: {response.text}")

def safe_append_blocks_to_notion(toggle_id: str, blocks: List[NotionBlock]) -> Tuple[Dict, List[str]]:
    try:
        response = append_blocks_to_notion(toggle_id, blocks)
        block_ids = [block['id'] for block in response['results']]
        for block_id in block_ids:
            block_tracker.add_block(block_id)
        return response, block_ids
    except Exception as e:
        logger.error(f"Error appending blocks to Notion: {str(e)}")
        raise

def append_section_to_notion(toggle_id: str, section_content: str, section_name: str) -> None:
    blocks: List[NotionBlock] = convert_content_to_blocks(section_content)
    try:
        response, block_ids = safe_append_blocks_to_notion(toggle_id, blocks)
    except Exception as e:
        logger.error(f"Failed to append {section_name} to Notion: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to append {section_name} to Notion")

def append_intro_to_notion(toggle_id: str, section_content: str) -> None:
    append_section_to_notion(toggle_id, section_content, "Intro")

def append_direct_quotes_to_notion(toggle_id: str, section_content: str) -> None:
    append_section_to_notion(toggle_id, section_content, "Direct Quotes")

def append_next_steps_to_notion(toggle_id: str, section_content: str) -> None:
    append_section_to_notion(toggle_id, section_content, "Next Steps")

def upload_transcript_to_notion(toggle_id: str, transcription: str) -> None:
    transcription_chunks: List[str] = chunk_text(transcription)
    try:
        for transcription_chunk in transcription_chunks:
            blocks: List[NotionBlock] = [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": parse_rich_text(transcription_chunk)
                    }
                }
            ]
            safe_append_blocks_to_notion(toggle_id, blocks)
    except Exception as e:
        logger.error(f"Error uploading transcript to Notion: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload transcript to Notion")

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def set_summarized_checkbox_on_notion_page_to_true(page_id: str) -> None:
    update_url = f"{NOTION_API_BASE_URL}/pages/{page_id}"
    headers = get_headers()
    data = {
        "properties": {
            "Summarized": {
                "checkbox": True
            }
        }
    }
    response = requests.patch(update_url, headers=headers, json=data)
    response.raise_for_status()

def create_toggle_block(page_id: str, title: str, color: str = "blue") -> str:
    toggle_block: ToggleBlock = {
        "object": "block",
        "type": "toggle",
        "toggle": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {
                        "content": title
                    },
                    "annotations": {
                        "bold": True,
                        "color": color
                    }
                }
            ],
        }
    }
    response, _ = safe_append_blocks_to_notion(page_id, [toggle_block])
    toggle_id = response['results'][0]['id']
    block_tracker.add_block(toggle_id)  # Track the toggle block itself
    return toggle_id

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def get_meetings_with_jumpshare_links_and_unsummarized_from_notion() -> List[Dict]:
    try:
        headers = get_headers()
        filter_data = {
            "filter": {
                "and": [
                    {"property": "Jumpshare Link", "url": {"is_not_empty": True}},
                    {"property": "Summarized", "checkbox": {"equals": False}}
                ]
            }
        }
        rainsound_meetings_database_url = f"https://api.notion.com/v1/databases/{rainsound_meetings_database_id}/query"
        response = requests.post(rainsound_meetings_database_url, headers=headers, json=filter_data)
        response.raise_for_status()
        notion_data = response.json()
        return notion_data.get('results', [])
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch meetings from Notion: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch meetings from Notion")