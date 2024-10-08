from fastapi import APIRouter, HTTPException, UploadFile
import traceback
import requests
from io import BytesIO
from .transcribe import transcribe
from .summarize import summarize_transcription  
from app.models import TranscriptionRequest
from app.lib.Env import (
    notion_api_key,
    rainsound_meetings_database_url
)
from app.lib.notion import update_notion_page_properties, append_transcript_to_notion
from app.lib.notion import chunk_text
import os
from app.lib.notion import (
    append_intro_to_notion,
    append_direct_quotes_to_notion,
    append_next_steps_to_notion
)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
api_router = APIRouter()
rainsound_meetings_database = f"https://api.notion.com/v1/databases/{rainsound_meetings_database_url}/query"

@api_router.post("/update_notion_with_transcript_and_summary")
async def update_notion_with_transcript_and_summary():
    print("Received request for updating Notion with transcript and summary.")
    try:
        # Get meetings that need to be updated from Notion
        meetings_to_summarize = get_meetings_with_jumpshare_links_and_unsummarized()
        print(f"Meetings to summarize: {meetings_to_summarize}")
        # Remove all but the first item in the array
        first_meeting_to_summarize = meetings_to_summarize[:1]
        print(f"Number of meetings to summarize: {len(first_meeting_to_summarize)}")
        for meeting in first_meeting_to_summarize:
            page_id = meeting.get('id')

            # Read transcription from transcription.txt
            with open('transcription.txt', 'r') as file:
                transcription = file.read()

            prompt_boilerplate_path = os.path.join(BASE_DIR, 'prompts/prompt_boilerplate/context.txt')

            with open(prompt_boilerplate_path, 'r') as f:
                prompt_boilerplate = f.read() 

            summary_chunks = []
            prompts_files = ["intro.txt", "direct_quotes.txt", "next_steps.txt"]
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

                    section_mapping = {
                        "intro.txt": append_intro_to_notion,
                        "direct_quotes.txt": append_direct_quotes_to_notion,
                        "next_steps.txt": append_next_steps_to_notion
                    }
                    append_function = section_mapping.get(file_name)

                    if append_function:
                        # Call the helper function to append the summary to Notion
                        append_function(
                            page_id=page_id,
                            section_content=decomposed_summary,
                            notion_api_key=notion_api_key
                        )
                    else:
                        # Handle unexpected filenames if necessary
                        raise ValueError(f"No append function defined for file: {file_name}")

            print(f"Summary chunks: {summary_chunks}")
        # Break up transcript and summary into chunks
        transcription_chunks = chunk_text(transcription)

        return
        # Loop over summary chunks and call the Notion function

        # Loop over transcription chunks and call the Notion function
        for transcription_chunk in transcription_chunks:
            await append_transcript_to_notion(page_id, transcription_chunk)

        # Update page properties
        await update_notion_page_properties(page_id)

        return {"message": "Success"}
    
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()  # Print the full traceback
        raise HTTPException(status_code=500, detail=f"Error updating Notion with transcript and summary: {e}")

def get_meetings_with_jumpshare_links_and_unsummarized():
    try:
        headers = {
            "Authorization": f"Bearer {notion_api_key}",
            "Notion-Version": "2022-06-28",
        }

        filter_data = {
            "filter": {
                "and": [
                    {"property": "Jumpshare Link", "url": {"is_not_empty": True}},
                    {"property": "Summarized", "checkbox": {"equals": False}}
                ]
            }
        }

        response = requests.post(rainsound_meetings_database, headers=headers, json=filter_data)
        if response.status_code == 200:
            notion_data = response.json()
            return notion_data.get('results', [])
        else:
            print(f"Failed to fetch meetings from Notion. Status code: {response.status_code}")
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch meetings from Notion")

    except Exception as e:
        print(e)
        traceback.print_exc()  # Print the full traceback
        raise HTTPException(status_code=500, detail="Error retrieving meetings from Notion.")


async def get_video_from_jumpshare_link(jumpshare_link):
    try:
        print("Received request for getting file from Jumpshare link.")

        modified_link = jumpshare_link + "+"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0"
        }

        response = requests.get(modified_link, headers=headers, allow_redirects=True)
        final_url = response.url

        video_response = requests.get(final_url, headers=headers, stream=True)
        if video_response.status_code == 200:
            video_content = BytesIO(video_response.content)
            video_content.seek(0)

            jumpshare_video = UploadFile(file=video_content, filename="video.mp4")
            return jumpshare_video
        else:
            print(f"Failed to download video. Status code: {video_response.status_code}")
            raise HTTPException(status_code=video_response.status_code, detail="Failed to download video")

    except Exception as e:
        print(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error processing Jumpshare link.")


async def get_transcription_and_summary_from_jumpshare_video(video_file: UploadFile):
    # Transcribe the audio
    transcription_response = await transcribe(video_file)

    # Extract transcription text from response
    transcription = transcription_response.get('transcription')

    # Check if transcription is a dictionary and extract the text field if necessary
    if isinstance(transcription, dict):
        transcription = transcription.get('text', '')

    # Summarize the transcription
    request = TranscriptionRequest(transcription=transcription)
    summary_response = await summarize_transcription(request)

    # Extract summary text from response
    summary = summary_response.get('summary')

    # Check if summary is a dictionary and extract the text field if necessary
    if isinstance(summary, dict):
        summary = summary.get('text', '')

    return transcription, summary
