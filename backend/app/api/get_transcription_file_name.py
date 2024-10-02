from fastapi import APIRouter
import os

api_router = APIRouter()

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))

@api_router.get("/get_transcription_file_name")
async def get_transcription_file_name():
    transcription_file_path = os.path.join(BASE_DIR, 'transcription.txt')

    if os.path.exists(transcription_file_path):
        with open(transcription_file_path, 'r') as file:
            first_line = file.readline().strip()  # Read the first line (file name)
            if first_line.startswith("File Name:"):
                file_name = first_line.replace("File Name:", "").strip()
                return {"file_not_found": False, "file_name": file_name}
            else:
                return {"file_not_found": True, "file_name": ""}
    else:
        return {"file_not_found": True, "file_name": ""}
