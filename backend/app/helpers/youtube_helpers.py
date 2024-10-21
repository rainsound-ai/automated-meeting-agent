
import re

def contains_the_string_youtube(link):
    link_lower = link.lower()
    return "youtube" in link_lower or "youtu.be" in link_lower

def title_is_not_a_url(link):
    # Regular expression pattern for URL validation
    pattern = re.compile(
        r'^'
        r'(?:(?:http|https)://)?'  # optional scheme
        r'(?:'
        r'(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'  # IP
        r')'
        r'(?::\d+)?'  # optional port
        r'(?:/[^/#?]+)*/?'  # path
        r'(?:\?[^#]*)?'  # query string
        r'(?:#.*)?$',  # fragment
        re.IGNORECASE)
    
    return not bool(pattern.match(link))
