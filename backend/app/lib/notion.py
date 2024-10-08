import re
import requests
from fastapi import HTTPException
from app.lib.Env import notion_api_key

# Configuration Constants
NOTION_VERSION = "2022-06-28"
NOTION_API_BASE_URL = "https://api.notion.com/v1"
HEADERS = {
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json"
}

def get_headers(notion_api_key):
    """
    Constructs the headers required for Notion API requests.
    
    :param notion_api_key: Your Notion integration's API key.
    :return: A dictionary of headers.
    """
    return {
        "Authorization": f"Bearer {notion_api_key}",
        **HEADERS
    }

def parse_bold(text):
    """
    Parses bold markdown-like directives in text.
    
    :param text: A string containing the text to parse.
    :return: A list of rich text objects with bold annotations where applicable.
    """
    rich_text = []
    
    # Regular expression to identify bold text
    bold_pattern = re.compile(r'\*\*([^*]+)\*\*')
    
    parts = bold_pattern.split(text)
    i = 0
    while i < len(parts):
        if i + 1 < len(parts):
            # Regular text before bold
            regular_text = parts[i]
            if regular_text:
                rich_text.append({
                    "type": "text",
                    "text": {
                        "content": regular_text
                    }
                })
            # Bold text
            bold_text = parts[i + 1]
            rich_text.append({
                "type": "text",
                "text": {
                    "content": bold_text
                },
                "annotations": {
                    "bold": True
                }
            })
            i += 2
        else:
            # Remaining text without bold
            remaining_text = parts[i]
            if remaining_text:
                rich_text.append({
                    "type": "text",
                    "text": {
                        "content": remaining_text
                    }
                })
            i += 1
    
    return rich_text

def parse_rich_text(text):
    """
    Parses a line of text and converts markdown-like directives into Notion's rich text format.
    
    :param text: A string containing the text to parse.
    :return: A list of rich text objects compatible with Notion API.
    """
    rich_text = []
    
    # Regular expressions for different markdown-like patterns
    link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
    # bold_pattern = re.compile(r'\*\*([^*]+)\*\*')
    
    # Split the text into parts based on links
    parts = link_pattern.split(text)
    i = 0
    while i < len(parts):
        if i + 2 < len(parts):
            # Text before link
            pre_link = parts[i]
            if pre_link:
                rich_text.extend(parse_bold(pre_link))
            # Link text and URL
            link_text = parts[i + 1]
            link_url = parts[i + 2]
            rich_text.append({
                "type": "text",
                "text": {
                    "content": link_text,
                    "link": {
                        "url": link_url
                    }
                }
            })
            i += 3
        else:
            # Remaining text without links
            remaining_text = parts[i]
            if remaining_text:
                rich_text.extend(parse_bold(remaining_text))
            i += 1
    
    return rich_text

def convert_line_to_block(line):
    """
    Converts a single line of text with markdown-like directives into a Notion block.
    
    :param line: A string containing the line to convert.
    :return: A Notion block object or None if the line is empty.
    """
    line = line.strip()
    if not line:
        return None
    
    # Section Titles
    if line.startswith("## "):
        title = line[3:].strip()
        return {
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": title
                        },
                        "annotations": {
                            "bold": True
                        }
                    }
                ]
            }
        }
    
    # Subsection Titles
    elif line.startswith("**") and line.endswith("**"):
        sub_title = line[2:-2].strip()
        return {
            "object": "block",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": sub_title
                        },
                        "annotations": {
                            "bold": True
                        }
                    }
                ]
            }
        }
    
    # Direct Quotes
    elif line.startswith('"') and line.endswith('"'):
        quote_text = line[1:-1].strip()
        return {
            "object": "block",
            "type": "quote",
            "quote": {
                "rich_text": parse_rich_text(quote_text)
            }
        }
    
    # Regular Paragraph
    else:
        return {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": parse_rich_text(line)
            }
        }

def convert_content_to_blocks(content):
    """
    Converts multi-line content into a list of Notion blocks.
    
    :param content: A string containing the multi-line content.
    :return: A list of Notion block objects.
    """
    blocks = []
    lines = content.split('\n')
    for line in lines:
        block = convert_line_to_block(line)
        if block:
            blocks.append(block)
    return blocks

def append_blocks_to_notion(toggle_id, blocks, notion_api_key):
    """
    Appends a list of blocks to a Notion page.
    
    :param page_id: The ID of the Notion page.
    :param blocks: A list of Notion block objects to append.
    :param notion_api_key: Your Notion integration's API key.
    :return: Response from Notion API.
    """
    blocks_url = f"{NOTION_API_BASE_URL}/blocks/{toggle_id}/children"
    headers = get_headers(notion_api_key)

    data = {
        "children": blocks
    }

    response = requests.patch(blocks_url, headers=headers, json=data)

    if response.status_code not in [200, 201]:
        raise HTTPException(status_code=500, detail=f"Failed to append blocks: {response.status_code} - {response.text}")

    return response.json()

def append_intro_to_notion(toggle_id, section_content, notion_api_key):
    """
    Appends the Intro section to a Notion page.
    
    :param page_id: The ID of the Notion page.
    :param intro_content: The content for the Intro section.
    :param notion_api_key: Your Notion integration's API key.
    """
    blocks = convert_content_to_blocks(section_content)
    append_blocks_to_notion(toggle_id, blocks, notion_api_key)

def append_direct_quotes_to_notion(toggle_id, section_content, notion_api_key):
    """
    Appends the Direct Quotes section to a Notion page.
    
    :param page_id: The ID of the Notion page.
    :param quotes_content: The content for the Direct Quotes section.
    :param notion_api_key: Your Notion integration's API key.
    """
    
    blocks = convert_content_to_blocks(section_content)
    append_blocks_to_notion(toggle_id, blocks, notion_api_key)

def append_next_steps_to_notion(toggle_id, section_content, notion_api_key):
    """
    Appends the Next Steps section to a Notion page.
    
    :param page_id: The ID of the Notion page.
    :param next_steps_content: The content for the Next Steps section.
    :param notion_api_key: Your Notion integration's API key.
    """
    blocks = convert_content_to_blocks(section_content)
    append_blocks_to_notion(toggle_id, blocks, notion_api_key)

def chunk_text(text, max_length=1999):
    """
    Splits the input text into chunks, each with a maximum length of `max_length` characters.
    
    :param text: The text to be chunked.
    :param max_length: The maximum length of each chunk.
    :return: A list of text chunks.
    """
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

def update_notion_page_properties(page_id):
    """
    Updates the 'Summarized' property of a Notion page to True.
    
    :param page_id: The ID of the Notion page.
    """
    update_url = f"{NOTION_API_BASE_URL}/pages/{page_id}"
    headers = get_headers(notion_api_key)
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

def append_transcript_to_notion(toggle_id, transcription_chunk, notion_api_key):
    """
    Appends a transcript chunk as a paragraph block to a Notion page.
    
    :param page_id: The ID of the Notion page.
    :param transcription_chunk: The text of the transcription chunk.
    :param notion_api_key: Your Notion integration's API key.
    """
    blocks = [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": parse_rich_text(transcription_chunk)
            }
        }
    ]
    append_blocks_to_notion(toggle_id, blocks, notion_api_key)

def create_toggle_block(page_id: str, title: str, color: str = "blue"):
    toggle_block = {
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

    # Send request to Notion to create the toggle
    notion_url = f"{NOTION_API_BASE_URL}/blocks/{page_id}/children"
    headers = get_headers(notion_api_key)
    response = requests.patch(notion_url, headers=headers, json={"children": [toggle_block]})
    
    if response.status_code == 200:
        # Extract and return the toggle block ID from the response
        toggle_id = response.json()['results'][0]['id']
        print(f"Toggle block with title '{title}' created. ID: {toggle_id}")
        return toggle_id
    else:
        raise Exception(f"Failed to create toggle block. Response: {response.content}")