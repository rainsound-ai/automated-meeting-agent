import re

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
    if line.startswith("# "):
        title = line[2:].strip()
        return {
            "object": "block",
            "type": "heading_1",
            "heading_1": {
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
    
    elif line.startswith("## "):
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

    elif line.startswith("### "):
        title = line[4:].strip()
        return {
            "object": "block",
            "type": "heading_3",
            "heading_3": {
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

    # Bullet Points
    elif line.startswith("- "):
        bullet_text = line[2:].strip()
        return {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": parse_rich_text(bullet_text)
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