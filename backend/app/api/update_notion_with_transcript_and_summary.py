from fastapi import APIRouter, HTTPException, UploadFile
import requests
from io import BytesIO
from .transcribe import transcribe
from .summarize import summarize_transcription  
from app.models import TranscriptionRequest
from app.lib.Env import (
    notion_api_key,
    rainsound_meetings_database_url
)
from app.lib.notion import update_notion_page_properties, append_summary_to_notion, append_transcript_to_notion
from app.lib.notion import chunk_text, split_summary

api_router = APIRouter()
rainsound_meetings_database = f"https://api.notion.com/v1/databases/{rainsound_meetings_database_url}/query"

@api_router.post("/update_notion_with_transcript_and_summary")
async def update_notion_with_transcript_and_summary():
    print("Received request for updating Notion with transcript and summary.")
    try:
        # Get meetings that need to be updated from Notion
        meetings_to_summarize = get_meetings_with_jumpshare_links_and_unsummarized()
        print(f"Meetings to summarize: {meetings_to_summarize}")

        for meeting in meetings_to_summarize:
            page_id = meeting.get('id')
            # jumpshare_link = meeting.get('properties', {}).get('Jumpshare Link', {}).get('url')

            # # Get video and transcription/summary
            # jumpshare_video = await get_video_from_jumpshare_link(jumpshare_link)
            # transcription, summary = await get_transcription_and_summary_from_jumpshare_video(jumpshare_video)

            # # Debugging output: Print transcription and summary after extraction
            # print("Transcription after extraction:", transcription)
            # print("Summary after extraction:", summary)

            # get the tranascription from trascription.txt

            # Read transcription from transcription.txt
            with open('transcription.txt', 'r') as file:
                transcription = file.read()

            # Read summary from sample_summary.txt
            with open('sample_summary.txt', 'r') as file:
                summary = file.read()

            # Ensure transcription and summary are strings before chunking
            if not isinstance(transcription, str):
                raise HTTPException(status_code=500, detail="Invalid transcription format")

            if not isinstance(summary, str):
                raise HTTPException(status_code=500, detail="Invalid summary format")
            
            # Break up transcript and summary into chunks
            transcription_chunks = chunk_text(transcription)
            summary_chunks = split_summary(summary)

            # Loop over summary chunks and call the Notion function
            for summary_chunk in summary_chunks:
                await append_summary_to_notion(page_id, summary_chunk)

            # Loop over transcription chunks and call the Notion function
            for transcription_chunk in transcription_chunks:
                await append_transcript_to_notion(page_id, transcription_chunk)

            # Update page properties
            await update_notion_page_properties(page_id)

        return {"message": "Success"}
    
    except Exception as e:
        print(f"Error: {e}")
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
