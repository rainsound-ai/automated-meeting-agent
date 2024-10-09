from typing import List, Dict
import requests
from fastapi import HTTPException
from app.lib.Env import notion_api_key, rainsound_meetings_database_id
import traceback
from app.services.chunk_text import chunk_text
from app.services.parse_markdown_to_notion_blocks import (
    convert_content_to_blocks, 
    parse_rich_text
)
from app.models import (
    NotionBlock, 
    ToggleBlock
)


# Configuration Constants
NOTION_VERSION = "2022-06-28"
NOTION_API_BASE_URL = "https://api.notion.com/v1"
HEADERS = {
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json"
}

def get_headers() -> Dict[str, str]:
    """
    Constructs the headers required for Notion API requests.
    
    :return: A dictionary of headers.
    """
    return {
        "Authorization": f"Bearer {notion_api_key}",
        **HEADERS
    }

def append_blocks_to_notion(toggle_id: str, blocks: List[NotionBlock]) -> Dict:
    """
    Appends a list of blocks to a Notion page.
    
    :param toggle_id: The ID of the Notion toggle block.
    :param blocks: A list of Notion block objects to append.
    :return: Response from Notion API.
    """
    blocks_url = f"{NOTION_API_BASE_URL}/blocks/{toggle_id}/children"
    headers = get_headers()

    data = {
        "children": blocks
    }

    response = requests.patch(blocks_url, headers=headers, json=data)

    if response.status_code not in [200, 201]:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to append blocks: {response.status_code} - {response.text}")

    return response.json()

def append_intro_to_notion(toggle_id: str, section_content: str) -> None:
    """
    Appends the Intro section to a Notion page.
    
    :param toggle_id: The ID of the Notion toggle block.
    :param section_content: The content for the Intro section.
    """
    blocks: List[NotionBlock] = convert_content_to_blocks(section_content)
    append_blocks_to_notion(toggle_id, blocks)

def append_direct_quotes_to_notion(toggle_id: str, section_content: str) -> None:
    """
    Appends the Direct Quotes section to a Notion page.
    
    :param toggle_id: The ID of the Notion toggle block.
    :param section_content: The content for the Direct Quotes section.
    """
    blocks: List[NotionBlock] = convert_content_to_blocks(section_content)
    append_blocks_to_notion(toggle_id, blocks)

def append_next_steps_to_notion(toggle_id: str, section_content: str) -> None:
    """
    Appends the Next Steps section to a Notion page.
    
    :param toggle_id: The ID of the Notion toggle block.
    :param section_content: The content for the Next Steps section.
    """
    blocks: List[NotionBlock] = convert_content_to_blocks(section_content)
    append_blocks_to_notion(toggle_id, blocks)

def upload_transcript_to_notion(page_id: str, transcription: str) -> None:
    transcription_chunks: List[str] = chunk_text(transcription)
    toggle_id: str = create_toggle_block(page_id, "Transcript", "orange")
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
        append_blocks_to_notion(toggle_id, blocks)

def set_summarized_checkbox_on_notion_page_to_true(page_id: str) -> None:
    """
    Updates the 'Summarized' property of a Notion page to True.
    
    :param page_id: The ID of the Notion page.
    """
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
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Failed to update page: {response.text}")

def append_transcript_to_notion(toggle_id: str, transcription_chunk: str) -> None:
    """
    Appends a transcript chunk as a paragraph block to a Notion page.
    
    :param toggle_id: The ID of the Notion toggle block.
    :param transcription_chunk: The text of the transcription chunk.
    """
    blocks: List[NotionBlock] = [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": parse_rich_text(transcription_chunk)
            }
        }
    ]
    append_blocks_to_notion(toggle_id, blocks)

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
                        "bold": True,  # Bold to simulate H1
                        "color": color
                    }
                }
            ],
        }
    }
    response = append_blocks_to_notion(page_id, [toggle_block])
    toggle_id = response['results'][0]['id']
    return toggle_id

def get_meetings_with_jumpshare_links_and_unsummarized_from_notion() -> List[Dict]:
    """
    Fetches meetings from Notion that have Jumpshare links and are unsummarized.
    
    :return: List of Notion meeting records.
    """
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
        if response.status_code == 200:
            notion_data = response.json()
            return notion_data.get('results', [])
        else:
            print(f"Failed to fetch meetings from Notion. Status code: {response.status_code}")
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch meetings from Notion")

    except Exception as e:
        print(e)
        traceback.print_exc()  
        raise HTTPException(status_code=500, detail="Error retrieving meetings from Notion.")
