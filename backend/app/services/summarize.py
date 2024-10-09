from typing import List
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
from app.models import (
    Transcription
)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
client = OpenAI(api_key=open_ai_api_key)

def get_file_path(file_name: str) -> str:
    return os.path.join(BASE_DIR, 'prompts', file_name)

async def summarize_transcription(transcription: Transcription, prompt: str) -> str:
    try:
        print("Received request for summarization.")
        transcription = transcription.strip()  # Assuming `content` is a field in `Transcription`
       
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
            print(f"GPT-4 API failed for final summarization with error: {e}")
            raise HTTPException(status_code=500, detail="Error while generating final summary.")

        return summary

    except Exception as e:
        print(f"An error occurred during the summarization process: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def decomposed_summarize_transcription_and_upload_to_notion(transcription: Transcription, page_id: str) -> None:
    prompt_boilerplate_path = os.path.join(BASE_DIR, 'prompts/prompt_boilerplate/context.txt')

    with open(prompt_boilerplate_path, 'r') as f:
        prompt_boilerplate = f.read() 

    summary_chunks = []
    prompts_files = ["intro.txt", "direct_quotes.txt", "next_steps.txt"]
    summary_toggle_id = create_toggle_block(page_id, "Summary", "green")
    
    for file_name in prompts_files:
        file_path = os.path.join(BASE_DIR, 'prompts', file_name) 
        with open(file_path, 'r') as f:
            prompt_content = f.read()
            full_prompt = prompt_boilerplate + prompt_content
            decomposed_summary = await summarize_transcription(transcription, full_prompt)
            
            summary_chunks.append({
                    'filename': file_name,
                    'summary': decomposed_summary
                }) 
            
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
