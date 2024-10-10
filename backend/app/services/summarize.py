from app.lib.Env import open_ai_api_key
from fastapi import HTTPException
import os
from openai import OpenAI
from app.services.notion import (
    create_toggle_block, 
    append_intro_to_notion,
    append_direct_quotes_to_notion,
    append_next_steps_to_notion,
)
from app.models import Transcription
from app.services.summary_eval_agent import evaluate_section  # Import the evaluation function

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
client = OpenAI(api_key=open_ai_api_key)

def get_file_path(file_name: str) -> str:
    return os.path.join(BASE_DIR, 'prompts', file_name)

async def summarize_transcription(transcription: str, prompt: str) -> str:
    try:
        print("Received request for summarization.")
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an assistant that provides structured meeting summaries."},
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

async def decomposed_summarize_transcription_and_upload_to_notion(transcription: Transcription, page_id: str) -> None:
    prompt_boilerplate_path = os.path.join(BASE_DIR, 'prompts/prompt_boilerplate/context.txt')
    with open(prompt_boilerplate_path, 'r') as f:
        prompt_boilerplate = f.read() 
    
    prompts_files = ["intro.txt", "direct_quotes.txt", "next_steps.txt"]
    
    max_attempts = 3
    quality_threshold = 0.7  # Adjust this value as needed
    
    summary_chunks = []
    full_summary = ""
    
    for file_name in prompts_files:
        section_name = file_name.split('.')[0].replace('_', ' ').title()
        file_path = os.path.join(BASE_DIR, 'prompts', file_name) 
        
        for attempt in range(max_attempts):
            with open(file_path, 'r') as f:
                prompt_content = f.read()
                full_prompt = prompt_boilerplate + prompt_content
                decomposed_summary = await summarize_transcription(transcription, full_prompt)
            
            # Evaluate the section
            try:
                evaluation_result = evaluate_section(transcription, decomposed_summary, section_name)
                section_score = evaluation_result.get('score', 0)  # Default to 0 if 'score' is not present
            except Exception as e:
                print(f"Error evaluating {section_name}: {e}")
                section_score = 0  # Set a default score if evaluation fails
            
            print(f"{section_name} - Attempt {attempt + 1}: Section score = {section_score}")
            
            if section_score >= quality_threshold:
                print(f"{section_name} meets quality standards. Moving to next section.")
                break
            elif attempt < max_attempts - 1:
                print(f"{section_name} quality below threshold. Retrying... (Attempt {attempt + 2}/{max_attempts})")
            else:
                print(f"Max attempts reached for {section_name}. Using the best version generated.")
        
        summary_chunks.append({
            'filename': file_name,
            'summary': decomposed_summary
        })
        full_summary += f"## {section_name}\n{decomposed_summary}\n\n"
    
    # Upload to Notion
    summary_toggle_id = create_toggle_block(page_id, "Summary", "green")
    
    for chunk in summary_chunks:
        file_name = chunk['filename']
        decomposed_summary = chunk['summary']
        
        # Map specific functions to file names
        section_mapping = {
            "intro.txt": append_intro_to_notion,
            "direct_quotes.txt": append_direct_quotes_to_notion,
            "next_steps.txt": append_next_steps_to_notion
        }
        append_function = section_mapping.get(file_name)
        
        if append_function:
            # Call the helper function to append the summary to Notion
            append_function(
                toggle_id=summary_toggle_id,
                section_content=decomposed_summary,
            )
        else:
            # Handle unexpected filenames if necessary
            raise ValueError(f"No append function defined for file: {file_name}")

    print("Summary uploaded to Notion successfully.")