# summarize.py
from fastapi import HTTPException
import os
import logging
from app.services.notion import (
    append_summary_to_notion,
    update_notion_title_with_llm_conversation_file_name
)
from app.models import Transcription
from app.services.eval_agent import evaluate_section
from app.services.get_openai_chat_response import get_openai_chat_response
# from tenacity import retry, stop_after_attempt, wait_exponential

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def read_file(file_path):
    with open(file_path, 'r') as f:
        return f.read()

async def summarize_transcription(transcription: str, prompt: str) -> str:
    try:
        logger.info("🌺 Received request for summarization.")
        summary = await get_openai_chat_response(prompt, transcription)
        return summary
    except Exception as e:
        logger.error(f"🚨 Unexpected error during summarization: {str(e)}")
        raise HTTPException(status_code=500, detail="Unexpected error during summarization")

async def decomposed_summarize_transcription_and_upload_to_notion(page_id, transcription: Transcription, toggle_id: str, is_llm_conversation=False, llm_conversation_file_name=None) -> None:
    max_attempts = 5
    quality_threshold = 0.8
    best_summary = None
    best_score = 0
    feedback = ""

    prompt_file = "llm_conversation_summary_prompt.txt" if is_llm_conversation else "summary_prompt.txt"
    prompt_content = read_file(os.path.join(BASE_DIR, 'prompts', prompt_file))

    for attempt in range(max_attempts):
        try:
            full_prompt = prompt_content + f"\n\nPrevious feedback:\n{feedback}"
            logger.info(f"💡 Attempt {attempt + 1}")
            
            # Generate new summary
            current_summary = await summarize_transcription(transcription, full_prompt)
            
            # Get fresh evaluation
            evaluation = await evaluate_section(transcription, current_summary, is_llm_conversation)
            current_score = evaluation['score']
            
            logger.info(f"💡 Score: {current_score}")
            
            # Update best if better
            if current_score > best_score:
                best_summary = current_summary
                best_score = current_score
                
            # Update feedback for next iteration
            feedback = f"Attempt {attempt + 1} feedback: {evaluation['feedback']}"
            
            if current_score >= quality_threshold:
                logger.info("💡 Meets quality standards")
                break
                
        except Exception as e:
            logger.error(f"🚨 Attempt {attempt + 1} failed: {str(e)}")
            if attempt == max_attempts - 1:
                raise Exception(f"Failed after {max_attempts} attempts") from e
            continue

    if not best_summary:
        raise Exception("Failed to generate valid summary")

    # Upload best summary to Notion
    await append_summary_to_notion(toggle_id, best_summary)

    if llm_conversation_file_name:
        formatted_name = llm_conversation_file_name.replace(".html", " ")
        await update_notion_title_with_llm_conversation_file_name(
            page_id, 
            f"LLM Conversation: {formatted_name}"
        )

    return best_summary