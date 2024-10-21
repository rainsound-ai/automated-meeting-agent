# summarize.py
from app.lib.Env import open_ai_api_key
from fastapi import HTTPException
import os
import logging
from openai import OpenAI, OpenAIError
from app.services.notion import (
    append_summary_to_notion,
    update_notion_title_with_llm_conversation_file_name
)
from app.models import Transcription
from app.services.eval_agent import evaluate_section
from tenacity import retry, stop_after_attempt, wait_exponential

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
client = OpenAI(api_key=open_ai_api_key)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def read_file(file_path):
    with open(file_path, 'r') as f:
        return f.read()

async def summarize_transcription(transcription: str, prompt: str) -> str:
    try:
        logger.info("🌺 Received request for summarization.")
        response = client.chat.completions.create(
            model="o1-mini",
            messages=[
                {"role": "user", "content": prompt + transcription}
            ]
        )
        summary = response.choices[0].message.content
        return summary
    except OpenAIError as e:
        logger.error(f"🚨 OpenAI API error: {str(e)}")
        raise HTTPException(status_code=500, detail="Error in OpenAI API call")
    except Exception as e:
        logger.error(f"🚨 Unexpected error during summarization: {str(e)}")
        raise HTTPException(status_code=500, detail="Unexpected error during summarization")

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))

async def decomposed_summarize_transcription_and_upload_to_notion(page_id, transcription: Transcription, toggle_id: str, is_llm_conversation=False, llm_conversation_file_name=None) -> None:

    prompt_file = "summary_prompt.txt"
    max_attempts = 5
    quality_threshold = 0.8
    
    prompt_content = read_file(os.path.join(BASE_DIR, 'prompts', prompt_file))
    
    best_summary = None
    best_score = 0
    feedback = ""

    if is_llm_conversation:
        print("🚨 Using LLM conversation summary prompt")
        prompt_file = "llm_conversation_summary_prompt.txt"
        prompt_content = read_file(os.path.join(BASE_DIR, 'prompts', prompt_file))

    for attempt in range(max_attempts):
        full_prompt = prompt_content + f"\n\nPrevious feedback:\n{feedback}"
        logger.info(f"💡 Prompt for summary - Attempt {attempt + 1}:\n{full_prompt}")
        
        try:
            decomposed_summary = await summarize_transcription(transcription, full_prompt)
            
            evaluation_result = evaluate_section(transcription, decomposed_summary, is_llm_conversation)
            section_score = evaluation_result["score"]
            section_feedback = evaluation_result["feedback"]
            
            logger.info(f"💡Attempt {attempt + 1}: Section score = {section_score}. is_llm_conversation = {is_llm_conversation}")
            
            # Update feedback instead of appending
            feedback = f"Attempt {attempt + 1} feedback: {section_feedback}"
            
            if section_score > best_score:
                best_summary = decomposed_summary
                best_score = section_score
            
            if section_score >= quality_threshold:
                logger.info("💡 Meets quality standards. Using this summary.")
                break
            elif attempt < max_attempts - 1:
                logger.info(f"💡 Quality below threshold. Retrying... (Attempt {attempt + 2}/{max_attempts})")
            else:
                logger.info(f"💡 Max attempts reached. Using the best version generated (score: {best_score}).")
        
        except Exception as e:
            logger.error(f"🚨 Error in attempt {attempt + 1}: {str(e)}")
            if attempt == max_attempts - 1:
                raise Exception(f"Failed to generate a valid summary after {max_attempts} attempts") from e

    if best_summary is None:
        raise Exception("Failed to generate any valid summary. Please check the input and evaluation process.")

    final_summary = decomposed_summary if section_score >= quality_threshold else best_summary
    
    logger.info(f"💡 Final summary score: {best_score}")
    
    # Here you would add the code to upload the final_summary to Notion
    await append_summary_to_notion(toggle_id=toggle_id, section_content=final_summary)

    if llm_conversation_file_name is not None:
        # Set the notion page title to the same title as the llm conversation file
        formatted_llm_conversation_file_name = llm_conversation_file_name.replace(".html", " ")
        await update_notion_title_with_llm_conversation_file_name(page_id, f"LLM Conversation: {formatted_llm_conversation_file_name}")

    return final_summary