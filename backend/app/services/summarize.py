# summarize.py
from app.lib.Env import open_ai_api_key
from fastapi import HTTPException
import os
import logging
from openai import OpenAI
from app.services.notion import (
    append_intro_to_notion,
    append_direct_quotes_to_notion,
    append_next_actions_to_notion,
)
from app.models import Transcription
from app.services.eval_agent import evaluate_section  # Import the evaluation function

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
client = OpenAI(api_key=open_ai_api_key)
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def summarize_transcription(transcription: str, prompt: str) -> str:
    try:
        print("Received request for summarization.")
        
        try:
            response = client.chat.completions.create(
                model="o1-mini",
                messages=[
                    # {"role": "system", "content": "You are an assistant that provides structured meeting summaries."},
                    {"role": "user", "content": prompt + transcription}
                ]
            )
            summary = response.choices[0].message.content
        except Exception as e:
            print(f"GPT-4 API failed for summarization with error: {e}")
            raise HTTPException(status_code=500, detail="Error while generating summary.")
        return summary
    except Exception as e:
        print(f"An error occurred during the summarization process: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def decomposed_summarize_transcription_and_upload_to_notion(transcription: Transcription, toggle_id: str) -> None:
    prompt_boilerplate_path = os.path.join(BASE_DIR, 'prompts/prompt_boilerplate/context.txt')
    with open(prompt_boilerplate_path, 'r') as f:
        prompt_boilerplate = f.read() 
    
    prompts_files = ["intro.txt", "direct_quotes.txt", "next_actions.txt"]
    
    max_attempts = 5
    quality_threshold = 0.8  # Adjust this value as needed
    
    summary_chunks = []
    full_summary = ""
    
    for file_name in prompts_files:
        section_name = file_name.split('.')[0].replace('_', ' ').title()
        file_path = os.path.join(BASE_DIR, 'prompts', file_name) 
        
        best_score = 0
        best_summary = ""
        best_feedback = ""
        
        for attempt in range(max_attempts):
            with open(file_path, 'r') as f:
                prompt_content = f.read()
                full_prompt = prompt_boilerplate + prompt_content
                decomposed_summary = await summarize_transcription(transcription, full_prompt)
            
            try:
                evaluation_result = evaluate_section(transcription, decomposed_summary, section_name)
                section_score = evaluation_result["section_score"]
                feedback = evaluation_result["feedback"]
                
                logger.info(f"{section_name} - Attempt {attempt + 1}: Section score = {section_score}")
                logger.info(f"Feedback: {feedback}")
                
                if section_score > best_score:
                    best_score = section_score
                    best_summary = decomposed_summary
                    best_feedback = feedback
                
                if section_score >= quality_threshold:
                    logger.info(f"{section_name} meets quality standards. Moving to next section.")
                    break
                elif attempt < max_attempts - 1:
                    logger.info(f"{section_name} quality below threshold. Retrying... (Attempt {attempt + 2}/{max_attempts})")
                else:
                    logger.info(f"Max attempts reached for {section_name}. Using the best version generated (score: {best_score}).")
            
            except Exception as e:
                logger.error(f"Error evaluating {section_name}: {str(e)}")
                if attempt == max_attempts - 1:
                    best_summary = decomposed_summary
                    best_feedback = "Evaluation failed"
        
        summary_chunks.append({
            'filename': file_name,
            'summary': best_summary,
            'score': best_score,
            'feedback': best_feedback
        })
        full_summary += f"## {section_name}\nScore: {best_score}\nFeedback: {best_feedback}\n\n{best_summary}\n\n"
    
    # Upload to Notion
    for chunk in summary_chunks:
        file_name = chunk['filename']
        decomposed_summary = chunk['summary']
        
        # Map specific functions to file names
        section_mapping = {
            "intro.txt": append_intro_to_notion,
            "direct_quotes.txt": append_direct_quotes_to_notion,
            "next_actions.txt": append_next_actions_to_notion
        }
        append_function = section_mapping.get(file_name)
        
        if append_function:
            # Call the helper function to append the summary to Notion
            try:
                await append_function(
                    toggle_id=toggle_id,
                    section_content=decomposed_summary,
                )
                logger.info(f"Successfully uploaded {file_name} to Notion")
            except Exception as e:
                logger.error(f"Failed to upload {file_name} to Notion: {str(e)}")
        else:
            # Handle unexpected filenames if necessary
            logger.warning(f"No append function defined for file: {file_name}")
    
    logger.info("Summary upload to Notion completed.")