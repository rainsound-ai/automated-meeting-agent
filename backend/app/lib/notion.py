import requests
from fastapi import HTTPException
from app.lib.Env import notion_api_key
import re

def chunk_text(text, max_length=2000):
    chunks = []
    while len(text) > max_length:
        chunk = text[:max_length]
        last_sentence_end = chunk.rfind('.')
        if last_sentence_end == -1:
            last_sentence_end = max_length
        current_chunk = text[:last_sentence_end + 1].strip()
        if current_chunk:
            chunks.append(current_chunk)
        text = text[last_sentence_end + 1:].strip()
    if text:
        chunks.append(text)
    return chunks

def split_summary(summary, max_length=2000):
    sections = re.split(r'(### .+)', summary)
    summary_chunks = []
    for i in range(1, len(sections), 2):
        section_header = sections[i]
        section_content = sections[i + 1]
        if len(section_header) + len(section_content) <= max_length:
            summary_chunks.append(section_header + section_content)
        else:
            content_chunks = chunk_text(section_content, max_length - len(section_header))
            summary_chunks.append(section_header + content_chunks[0])
            summary_chunks.extend(content_chunks[1:])
    return summary_chunks

async def update_notion_page_properties(page_id):
    update_url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {
        "Authorization": f"Bearer {notion_api_key}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
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

async def append_summary_to_notion(page_id, summary_chunk):
    blocks_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    headers = {
        "Authorization": f"Bearer {notion_api_key}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    # Append one summary chunk at a time
    data = {
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": summary_chunk
                            }
                        }
                    ]
                }
            }
        ]
    }
    response = requests.patch(blocks_url, headers=headers, json=data)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Failed to append summary block: {response.text}")

async def append_transcript_to_notion(page_id, transcription_chunk):
    blocks_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    headers = {
        "Authorization": f"Bearer {notion_api_key}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    # Append one transcription chunk at a time
    data = {
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": transcription_chunk
                            }
                        }
                    ]
                }
            }
        ]
    }
    response = requests.patch(blocks_url, headers=headers, json=data)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Failed to append transcript block: {response.text}")
