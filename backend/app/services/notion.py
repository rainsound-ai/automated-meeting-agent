from typing import List, Dict, Tuple
import requests
import json
from fastapi import HTTPException
from app.lib.Env import notion_api_key, rainsound_link_summary_database_id, rainsound_meeting_summary_database_id
import logging
from app.services.chunk_text_with_2000_char_limit_for_notion import chunk_text_with_2000_char_limit_for_notion
from app.services.parse_markdown_to_notion_blocks import (
    convert_content_to_blocks, 
    parse_rich_text
)
from app.models import (
    NotionBlock, 
    ToggleBlock
)
# from tenacity import retry, stop_after_attempt, wait_exponential

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

# @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def append_blocks_to_notion(toggle_id: str, blocks: List[NotionBlock]) -> Dict:
    blocks_url = f"{NOTION_API_BASE_URL}/blocks/{toggle_id}/children"
    headers = get_headers()
    data = {"children": blocks}
    response = requests.patch(blocks_url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()

async def rollback_blocks():
    for block_id in block_tracker.get_blocks():
        await delete_block(block_id)
    block_tracker.clear()

# @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def delete_block(block_id: str):
    url = f"{NOTION_API_BASE_URL}/blocks/{block_id}"
    headers = get_headers()
    response = requests.delete(url, headers=headers)
    if response.status_code != 200:
        logger.error(f"🚨 Failed to delete block {block_id}: {response.text}")

async def safe_append_blocks_to_notion(toggle_id: str, blocks: List[NotionBlock]) -> Tuple[Dict, List[str]]:
    try:
        response = await append_blocks_to_notion(toggle_id, blocks)
        block_ids = [block['id'] for block in response['results']]
        for block_id in block_ids:
            block_tracker.add_block(block_id)
        return response, block_ids
    except Exception as e:
        logger.error(f"🚨 Error appending blocks to Notion: {str(e)}")
        raise

async def append_summary_to_notion(toggle_id: str, section_content: str) -> None:
    blocks: List[NotionBlock] = convert_content_to_blocks(section_content)
    try:
        await safe_append_blocks_to_notion(toggle_id, blocks)
    except Exception as e:
        logger.error(f"🚨 Failed to append summary to Notion: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to append summary to Notion")

async def upload_transcript_to_notion(toggle_id: str, transcription: str) -> None:
    transcription_chunks: List[str] = chunk_text_with_2000_char_limit_for_notion(transcription)
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
            await safe_append_blocks_to_notion(toggle_id, blocks)
    except Exception as e:
        logger.error(f"🚨 Error uploading transcript to Notion: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload transcript to Notion")

# @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def set_summarized_checkbox_on_notion_page_to_true(page_id: str) -> None:
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

async def create_toggle_block(page_id: str, title: str, color: str = "blue") -> str:
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
    response, _ = await safe_append_blocks_to_notion(page_id, [toggle_block])
    toggle_id = response['results'][0]['id']
    block_tracker.add_block(toggle_id)  # Track the toggle block itself
    return toggle_id

# @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def get_unsummarized_links_from_notion() -> List[Dict]:
    try:
        headers = get_headers()
        
        # Corrected filter syntax according to Notion API
        filter_data = {
            "filter": {
                "and": [
                    {
                        "property": "Summarized",
                        "checkbox": {
                            "equals": False
                        }
                    },
                    {
                        "or": [
                            {
                                "property": "Link",
                                "url": {
                                    "is_not_empty": True  # Changed from is_empty: False
                                }
                            },
                            {
                                "property": "LLM Conversation",
                                "files": {
                                    "is_not_empty": True  # Changed from is_empty: False
                                }
                            }
                        ]
                    }
                ]
            }
        }

        # Add debugging to see what we're sending
        logger.debug(f"Sending filter to Notion: {json.dumps(filter_data, indent=2)}")

        rainsound_link_summary_database_url = f"https://api.notion.com/v1/databases/{rainsound_link_summary_database_id}/query"
        
        response = requests.post(
            rainsound_link_summary_database_url, 
            headers=headers, 
            json=filter_data
        )
        
        # Add debugging for the response
        if response.status_code != 200:
            logger.error(f"Notion API Error: {response.status_code}")
            logger.error(f"Response body: {response.text}")
            
        response.raise_for_status()
        notion_data = response.json()
        
        logger.debug(f"Retrieved {len(notion_data.get('results', []))} links from Notion")
        
        return notion_data.get('results', [])
        
    except requests.exceptions.RequestException as e:
        logger.error(f"🚨 Failed to fetch links from Notion: {str(e)}")
        # Add more detailed error information
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response body: {e.response.text}")
        raise HTTPException(status_code=500, detail="Failed to fetch links from Notion")

async def get_unsummarized_meetings_from_notion() -> List[Dict]:
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
        rainsound_meetings_database_url = f"https://api.notion.com/v1/databases/{rainsound_meeting_summary_database_id}/query"
        response = requests.post(rainsound_meetings_database_url, headers=headers, json=filter_data)
        response.raise_for_status()
        notion_data = response.json()
        return notion_data.get('results', [])
    except requests.exceptions.RequestException as e:
        logger.error(f"🚨 Failed to fetch meetings from Notion: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch meetings from Notion")

async def update_notion_title_for_summarized_item(page_id, llm_conversation_file_name):
    # update the title of the Notion page with the LLM conversation file name
    update_url = f"{NOTION_API_BASE_URL}/pages/{page_id}"
    headers = get_headers()
    data = {
        "properties": {
            "Title": {
                "title": [
                    {
                        "text": {
                            "content": llm_conversation_file_name
                        }
                    }
                ]
            }
        }
    }
    response = requests.patch(update_url, headers=headers, json=data)
    response.raise_for_status()