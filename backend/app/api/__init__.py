from fastapi import APIRouter
from .summarize import (
    api_router as summarize_router,
)
from .transcribe import (
    api_router as transcribe_router,
)
from .get_transcription_file_name import (
    api_router as get_transcription_file_name_router,
)
api_router = APIRouter()
api_router.include_router(summarize_router, prefix="")
api_router.include_router(transcribe_router, prefix="")
api_router.include_router(get_transcription_file_name_router, prefix="")