from fastapi import APIRouter,  HTTPException
import requests
from app.lib.Env import (
    notion_api_key,
    rainsound_meetings_database_url
)
api_router = APIRouter()
print("rainsound_meetings_database_url: ", rainsound_meetings_database_url)
rainsound_meetings_database = f"https://api.notion.com/v1/databases/{rainsound_meetings_database_url}/query"

# Define the input model for transcription
@api_router.post("/update_notion_with_transcript_and_summary")
def update_notion_with_transcript_and_summary():
  try:
    print("Received request for updating notion with transcript and summary.")
    meetings_to_update = get_meetings_with_jumpshare_links_but_no_transcript_or_summary_from_notion()
    print(f"Meetings to update: {meetings_to_update}")
    meeting_file = get_file_from_jumpshare_link("https://jmp.sh/Xq0CiuDe")
    print(f"Meeting file: {meeting_file}")
  except Exception as e:
    print(e)
    raise HTTPException(status_code=500, detail="Error updating notion with transcript and summary.")

def get_meetings_with_jumpshare_links_but_no_transcript_or_summary_from_notion():
    try:
        print("Received request for getting meetings with Jumpshare links but no transcript or summary from Notion.")

        headers = {
            "Authorization": f"Bearer {notion_api_key}",
            "Notion-Version": "2022-06-28",
        }

        # Request to query the meeting database
        response = requests.post(rainsound_meetings_database, headers=headers)

        if response.status_code == 200:
            notion_data = response.json()

            # Filter pages with a Jumpshare link but without a transcript or summary
            meetings_with_jumpshare_links_but_no_transcript_or_summary = []

            for meeting in notion_data["results"]:
                properties = meeting["properties"]
                jumpshare_link = properties.get("Jumpshare Link", {}).get("url")
                transcript = properties.get("Transcript", {}).get("rich_text", [])
                summary = properties.get("Summary", {}).get("rich_text", [])

                # Check if the page has a Jumpshare link and no transcript/summary
                if jumpshare_link and not transcript and not summary:
                    meetings_with_jumpshare_links_but_no_transcript_or_summary.append(meeting)

            return meetings_with_jumpshare_links_but_no_transcript_or_summary

        else:
            print(f"Failed to fetch data from Notion. Status code: {response.status_code}, Response: {response.text}")
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch Notion data")

    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Error getting meetings with Jumpshare links but no transcript or summary from Notion.")

def get_file_from_jumpshare_link(jumpshare_link):
    try:
        print("Received request for getting file from Jumpshare link.")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0"
        }

        # Send a GET request to the Jumpshare link to download the file
        response = requests.get(jumpshare_link, headers=headers, stream=True)

        if response.status_code == 200:
            # Extract filename from headers (if available) or link
            filename = jumpshare_link.split("/")[-1]

            # Save the file to local storage
            with open(filename, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)

            print(f"File {filename} downloaded successfully.")
            return filename
        else:
            print(f"Failed to download file from Jumpshare. Status code: {response.status_code}")
            raise HTTPException(status_code=response.status_code, detail="Failed to download file from Jumpshare")

    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Error getting file from Jumpshare link.")