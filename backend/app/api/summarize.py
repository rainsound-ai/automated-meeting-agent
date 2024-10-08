from app.lib.Env import open_ai_api_key
from fastapi import APIRouter,  HTTPException
import os
import warnings
from openai import OpenAI
from app.lib.JsonSchemas import TranscriptionRequest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))

client = OpenAI(api_key=open_ai_api_key)

# Ignore torch warning 
warnings.filterwarnings("ignore", category=FutureWarning)

api_router = APIRouter()

# Define the input model for transcription
@api_router.post("/summarize")

# get the file path for evry file in prompts
def get_file_path(file_name):
    return os.path.join(BASE_DIR, 'prompts', file_name)

async def summarize_transcription(transcription: TranscriptionRequest, prompt: str):
    try:
        print("Received request for summarization.")
        transcription = transcription.strip()
       

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