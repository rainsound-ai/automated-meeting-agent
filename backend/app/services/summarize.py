# summarize.py
from app.lib.Env import open_ai_api_key
from fastapi import HTTPException
import os
import logging
from openai import OpenAI, OpenAIError
from app.services.notion import (
    append_intro_to_notion,
    append_direct_quotes_to_notion,
    append_next_actions_to_notion,
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
        print("Received request for summarization.")
        response = client.chat.completions.create(
            model="o1-mini",
            messages=[
                {"role": "user", "content": prompt + transcription}
            ]
        )
        summary = response.choices[0].message.content
        return summary
    except OpenAIError as e:
        logger.error(f"OpenAI API error: {str(e)}")
        raise HTTPException(status_code=500, detail="Error in OpenAI API call")
    except Exception as e:
        logger.error(f"Unexpected error during summarization: {str(e)}")
        raise HTTPException(status_code=500, detail="Unexpected error during summarization")

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def upload_to_notion(append_function, toggle_id, section_content):
    await append_function(toggle_id=toggle_id, section_content=section_content)

async def decomposed_summarize_transcription_and_upload_to_notion(transcription: Transcription, toggle_id: str) -> None:
    prompt_boilerplate = read_file(os.path.join(BASE_DIR, 'prompts/prompt_boilerplate/context.txt'))
    prompts_files = ["intro.txt", "direct_quotes.txt", "next_actions.txt"]
    max_attempts = 5
    quality_threshold = 0.8
    summary_chunks = []
    
    for file_name in prompts_files:
        section_name = file_name.split('.')[0].replace('_', ' ').title()
        prompt_content = read_file(os.path.join(BASE_DIR, 'prompts', file_name))
        
        best_score = 0
        best_summary = ""
        feedback_history = ""

        for attempt in range(max_attempts):
            full_prompt = prompt_boilerplate + prompt_content + f"\n\nPrevious feedback:\n{feedback_history}"
            print(f"🚨 Prompt for {section_name} - Attempt {attempt + 1}:\n{full_prompt}")
            decomposed_summary = await summarize_transcription(transcription, full_prompt)
            
            try:
                evaluation_result = evaluate_section(transcription, decomposed_summary, section_name)
                section_score = evaluation_result["score"]
                section_feedback = evaluation_result["feedback"]
                
                logger.info(f"{section_name} - Attempt {attempt + 1}: Section score = {section_score}")
                feedback_history = f"Attempt {attempt + 1} feedback: {section_feedback}"
                
                if section_score > best_score:
                    best_summary = decomposed_summary
                    best_score = section_score
                    print("🚨 updating best summary for", file_name)
                    print("🚨 best score:", best_score)
                
                if section_score >= quality_threshold:
                    logger.info(f"{section_name} meets quality standards. Moving to next section.")
                    break
                elif attempt < max_attempts - 1:
                    logger.info(f"{section_name} quality below threshold. Retrying... (Attempt {attempt + 2}/{max_attempts})")
                else:
                    logger.info(f"Max attempts reached for {section_name}. Using the best version generated (score: {best_score}).")
            
            except Exception as e:
                logger.error(f"Error evaluating {section_name}: {str(e)}")

        print("appending summary chunk to summary chunks for", file_name)
        summary_chunks.append({
            'filename': file_name,
            'summary': best_summary,
        })
    
    section_mapping = {
        "intro.txt": append_intro_to_notion,
        "direct_quotes.txt": append_direct_quotes_to_notion,
        "next_actions.txt": append_next_actions_to_notion
    }
    
    print("Number of summary chunks:", len(summary_chunks))
    for chunk in summary_chunks:
        file_name = chunk['filename']
        decomposed_summary = chunk['summary']
        append_function = section_mapping.get(file_name)
        print("appending summary chunk to notion for", file_name)
        
        if append_function:
            try:
                print("🚨About to upload this summary section to notion:", decomposed_summary)
                await upload_to_notion(append_function, toggle_id, decomposed_summary)
                logger.info(f"Successfully uploaded {file_name} summary section to Notion")
            except Exception as e:
                logger.error(f"Failed to upload {file_name} summary section to Notion after retries: {str(e)}")
        else:
            logger.warning(f"No append function defined for file: {file_name}")
    
    logger.info("Summary upload to Notion completed.")