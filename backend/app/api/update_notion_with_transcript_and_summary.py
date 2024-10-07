import os
from fastapi import APIRouter, HTTPException, UploadFile
import requests
from io import BytesIO
from starlette.datastructures import UploadFile  # Import UploadFile to mimic actual file
from .transcribe import transcribe  # Assuming transcribe is defined here

api_router = APIRouter()

@api_router.post("/update_notion_with_transcript_and_summary")
async def update_notion_with_transcript_and_summary():
    try:
        print("Received request for updating notion with transcript and summary.")
        transcription = await get_file_from_jumpshare_link("https://jmp.sh/Xq0CiuDe")
        print(f"Transcription: {transcription}")
        return {"message": "Success", "transcription": transcription}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Error updating notion with transcript and summary.")


async def get_file_from_jumpshare_link(jumpshare_link):
    try:
        print("Received request for getting file from Jumpshare link.")

        # Add '+' to the end of the link to get the direct download page
        modified_link = jumpshare_link + "+"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0"
        }

        # This will follow all redirects and return the final URL
        response = requests.get(modified_link, headers=headers, allow_redirects=True)
        final_url = response.url
        print(f"Final video URL: {final_url}")

        # Download the video content
        video_response = requests.get(final_url, headers=headers, stream=True)

        if video_response.status_code == 200:
            # Store the video content in memory (BytesIO)
            video_content = BytesIO(video_response.content)
            video_content.seek(0)  # Reset the pointer to the start of the stream

            # Mimic UploadFile by wrapping the BytesIO in an UploadFile object
            upload_file = UploadFile(file=video_content, filename="video.mp4")

            # Now, call the transcribe function with the UploadFile object
            transcription = await transcribe(upload_file)
            return transcription
        else:
            print(f"Failed to download video. Status code: {video_response.status_code}")
            raise HTTPException(status_code=video_response.status_code, detail="Failed to download video")

    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Error processing Jumpshare link.")
