import re

def link_is_jumpshare_link(url: str) -> bool:
    """
    Check if a URL is a valid Jumpshare link.
    Returns True if the URL matches the Jumpshare pattern, False otherwise.
    
    Example:
    >>> is_jumpshare_link("https://jmp.sh/vFnfU1ek")
    True
    >>> is_jumpshare_link("https://example.com")
    False
    """
    
    # Pattern matches:
    # - http:// or https:// (optional)
    # - jmp.sh/
    # - followed by alphanumeric characters
    pattern = r'^(?:https?://)?jmp\.sh/[a-zA-Z0-9]+$'
    string_url = str(url)
    string_url = string_url.strip()
    
    return bool(re.match(pattern, string_url))