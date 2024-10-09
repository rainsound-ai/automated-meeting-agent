from fastapi import APIRouter
from .update_notion_with_transcript_and_summary import (
    api_router as update_notion_with_transcript_and_summary_router,
)

api_router = APIRouter()
api_router.include_router(update_notion_with_transcript_and_summary_router, prefix="")