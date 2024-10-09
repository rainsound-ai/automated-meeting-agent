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