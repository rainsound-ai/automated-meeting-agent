from app.helpers.jumpshare_helper import link_is_jumpshare_link

def link_is_none_and_therefore_this_must_be_an_llm_conversation_html_file(link): 
    if link is None:
        if not link_is_jumpshare_link(link):
            return True
    return False