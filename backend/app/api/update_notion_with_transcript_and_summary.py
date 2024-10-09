from fastapi import APIRouter, HTTPException, UploadFile
import traceback
import requests
from io import BytesIO
from app.services.transcribe import transcribe
from app.services.summarize import decomposed_summarize_transcription_and_upload_to_notion  
import os
from app.services.notion import (
    set_summarized_checkbox_on_notion_page_to_true,
    upload_transcript_to_notion,
    get_meetings_with_jumpshare_links_and_unsummarized_from_notion
)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
api_router = APIRouter()

@api_router.post("/update_notion_with_transcript_and_summary")
async def update_notion_with_transcript_and_summary():
    print("Received request for updating Notion with transcript and summary.")

    try:
        meetings_to_summarize = get_meetings_with_jumpshare_links_and_unsummarized_from_notion()
        print("Preparing to add summaries and transcripts to these meetings:")
        for meeting in meetings_to_summarize:
            print(meeting.get('properties').get('Name').get('title')[0].get('text').get('content'))

        # Remove all but the first item in the array
        first_meeting_to_summarize = meetings_to_summarize[:1]

        for meeting in first_meeting_to_summarize:
            page_id = meeting.get('id')

            jumpshare_video = await get_video_from_jumpshare_link(meeting.get('properties').get('Jumpshare Link').get('url'))

            transcription = await transcribe(jumpshare_video)

            await decomposed_summarize_transcription_and_upload_to_notion(transcription, page_id)

            upload_transcript_to_notion(page_id, transcription)

            set_summarized_checkbox_on_notion_page_to_true(
                page_id=page_id,
            )

        return {"message": "Success"}
    
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()  
        raise HTTPException(status_code=500, detail=f"Error updating Notion with transcript and summary: {e}")

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