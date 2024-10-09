from app.lib.Env import environment
import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import api_router
from app.api.update_notion_with_transcript_and_summary import update_notion_with_transcript_and_summary

app = FastAPI()

# CORS settings
frontend_url = "https://meeting-agent-frontend.onrender.com"

# We want this service's endpoints to be available from /api.
prefix = "/api"
print(f"Running in {environment} environment")
if environment == "dev":
    print("setting up CORS middleware for dev")
    prefix = prefix
    logger = logging.getLogger("uvicorn")
    logger.warning("Running in development mode - allowing CORS for all origins")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins in development
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # In production, allow only the frontend URL
    print("setting up CORS middleware for production")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[frontend_url],  # Allow only the SvelteKit frontend
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=prefix)

@app.on_event("startup")
async def startup_event():
    print("Running Notion update on startup")
    await update_notion_with_transcript_and_summary()

if environment == "dev":
    if __name__ == "__main__":
        uvicorn.run(app="main:app", host="0.0.0.0", reload=True)
